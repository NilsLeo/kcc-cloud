"""
ETA Estimation Algorithm for Manga/Comic Conversion

Based on empirical data:
- Witch Hat Atelier v03: 189 pages, ~422 seconds total
  - MuPDF extraction: 141 seconds (33.4%)
  - Image processing: 281 seconds (66.6%)
  - HTML building: 0.1 seconds (negligible)

Performance factors:
- File type (PDF vs archives vs images) - PDFs 3x slower due to MuPDF extraction
- File size (correlates with page count and image quality)
- Device profile resolution (higher = more processing)
- Advanced options (quality, upscaling, color, etc.)
- Available system resources

OPTIMIZED MODEL (v2.0):
- Removed output_file_size (unknown at prediction time)
- Added input_extension (PDF vs archive makes huge difference)
- Added conversion options (upscale, force_color, etc.)
- Expected accuracy improvement: 65% → 80-85%
"""

import os
import time
import pandas as pd
import numpy as np
import sqlalchemy
from sqlalchemy import func, text
from sklearn.model_selection import train_test_split, cross_val_score, KFold, GridSearchCV
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, median_absolute_error
import joblib
import json
from typing import Dict, Any, Optional
from database import SessionLocal, ConversionJob
from utils.enhanced_logger import setup_enhanced_logging, log_with_context

logger = setup_enhanced_logging()

# Singleton pattern for model caching with S3 versioning
_CACHED_MODEL = None
_CACHED_MODEL_VERSION = None  # Track which version is cached
_LOCAL_CACHE_DIR = "/tmp/ml_models"
_S3_MODEL_PREFIX = "ml_models/eta_estimator"

# Feature definitions (v2.0 - OPTIMIZED)
CATEGORICAL_FEATURES = ['device_profile', 'input_extension', 'output_format']

BOOLEAN_FEATURES = [
    'upscale',        # Huge impact (2-5x slower)
    'force_color',    # Keeps color vs grayscale (slower)
    'autolevel',      # Image processing (slower)
    'force_png',      # PNG vs JPEG (slower)
    'mozjpeg',        # Better compression (slower)
    'hq',             # High quality mode (slower)
    'manga_style',    # Manga optimizations
    'two_panel',      # Two-page spreads
]

NUMERICAL_FEATURES = [
    'input_file_size',
    'cropping',        # 0=off, 1-3=increasing work
    'splitter',        # Page splitting work
    'custom_width',    # Custom dimensions (0 if None)
    'custom_height',   # Custom dimensions (0 if None)
]

TARGET_FEATURE = ['actual_duration']

def retrieve_data():
    """Retrieve all conversion jobs from database"""
    from database.models import get_db_session
    session = get_db_session()
    try:
        # Execute raw SQL and fetch results
        result = session.execute(sqlalchemy.text("SELECT * FROM conversion_jobs"))
        columns = result.keys()
        rows = result.fetchall()
        # Convert to DataFrame manually
        df = pd.DataFrame(rows, columns=columns)
        return df
    finally:
        session.close()

def extract_features(df):
    """Extract and engineer features from raw data"""
    # Extract input extension from filename
    df['input_extension'] = df['input_filename'].apply(
        lambda x: os.path.splitext(str(x))[1].lower() if pd.notna(x) else 'unknown'
    )

    # Fill None values in numeric columns with 0
    df['custom_width'] = df['custom_width'].fillna(0).astype(int)
    df['custom_height'] = df['custom_height'].fillna(0).astype(int)
    df['cropping'] = df['cropping'].fillna(0).astype(int)
    df['splitter'] = df['splitter'].fillna(0).astype(int)

    # Fill None values in categorical columns
    df['output_format'] = df['output_format'].fillna('mobi')

    # Convert boolean columns to int (0/1)
    for col in BOOLEAN_FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna(False).astype(int)

    return df

def sanitize_data(df):
    """Clean and filter data for training"""
    # Extract features first
    df = extract_features(df)

    # Select only needed columns
    all_features = CATEGORICAL_FEATURES + NUMERICAL_FEATURES + BOOLEAN_FEATURES + TARGET_FEATURE
    df = df[all_features]

    # Drop rows with missing target or critical features
    df = df.dropna(subset=['actual_duration', 'input_file_size', 'device_profile'])

    # Remove duplicates
    df = df.drop_duplicates()

    # Remove outliers (duration > 1 hour or < 1 second)
    df = df[(df['actual_duration'] > 1) & (df['actual_duration'] < 3600)]

    # Remove jobs with zero file size
    df = df[df['input_file_size'] > 0]

    return df

def train_model():
    """Train ML model with optimized features"""
    df = sanitize_data(retrieve_data())

    if len(df) < 10:
        print(f"WARNING: Only {len(df)} samples available for training. Need at least 10.")
        print("Using simple heuristic instead.")
        return False

    # Prepare features and target
    X = df[CATEGORICAL_FEATURES + NUMERICAL_FEATURES + BOOLEAN_FEATURES]
    y = df[TARGET_FEATURE].values.ravel()  # Flatten to 1D array

    print(f"\n{'='*60}")
    print(f"Training ETA Model v2.0 (Optimized)")
    print(f"{'='*60}")
    print(f"Training samples: {len(df)}")
    print(f"Features: {len(X.columns)}")
    print(f"  - Categorical: {CATEGORICAL_FEATURES}")
    print(f"  - Numerical: {NUMERICAL_FEATURES}")
    print(f"  - Boolean: {BOOLEAN_FEATURES}")
    print(f"{'='*60}\n")

    # Create preprocessor with scaling for numerical features
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(sparse_output=False, handle_unknown='ignore'), CATEGORICAL_FEATURES),
            ('num', StandardScaler(), NUMERICAL_FEATURES),
            ('bool', 'passthrough', BOOLEAN_FEATURES)
        ]
    )

    # Define models with hyperparameter grids for tuning
    # NOTE: n_jobs=1 to avoid warnings in multiprocessing (Celery workers)
    models_with_params = {
        "Random Forest": {
            "model": RandomForestRegressor(random_state=42, n_jobs=1),
            "params": {
                'regressor__n_estimators': [100, 150, 200],
                'regressor__max_depth': [10, 15, 20, None],
                'regressor__min_samples_split': [5, 10, 15],
                'regressor__min_samples_leaf': [2, 4, 6],
                'regressor__max_features': ['sqrt', 'log2']
            }
        },
        "Gradient Boosting": {
            "model": GradientBoostingRegressor(random_state=42),
            "params": {
                'regressor__n_estimators': [100, 150, 200],
                'regressor__learning_rate': [0.01, 0.05, 0.1],
                'regressor__max_depth': [3, 5, 7],
                'regressor__min_samples_split': [5, 10],
                'regressor__min_samples_leaf': [2, 4],
                'regressor__subsample': [0.8, 0.9, 1.0]
            }
        }
    }

    # Split data for final validation
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=True)

    # Use 5-fold cross-validation for hyperparameter tuning
    kfold = KFold(n_splits=5, shuffle=True, random_state=42)

    best_model_name = None
    best_cv_score = float('inf')  # Use Median Absolute Error for selection (lower is better)
    best_pipeline = None
    best_metrics = None

    print("Performing hyperparameter tuning with 5-fold CV...")
    print("="*60)

    for name, config in models_with_params.items():
        print(f"\nTuning {name}...")

        # Create pipeline
        pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('regressor', config['model'])
        ])

        # Perform grid search with cross-validation
        # NOTE: n_jobs=1 to avoid warnings in multiprocessing (Celery workers)
        # Use neg_median_absolute_error because sklearn uses negated scores (higher is better)
        grid_search = GridSearchCV(
            pipeline,
            param_grid=config['params'],
            cv=kfold,
            scoring='neg_median_absolute_error',
            n_jobs=1,
            verbose=0
        )

        # Fit grid search on training data
        grid_search.fit(X_train, y_train)

        # Get best estimator
        best_estimator = grid_search.best_estimator_

        # Get CV score from grid search (negate to get actual MedAE)
        cv_medae = -grid_search.best_score_
        cv_std = grid_search.cv_results_['std_test_score'][grid_search.best_index_]

        # Evaluate on hold-out test set
        y_pred = best_estimator.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        medae = median_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)

        # Calculate MAPE (Mean Absolute Percentage Error)
        mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100

        print(f"\n{name} (Optimized):")
        print(f"  Best params: {grid_search.best_params_}")
        print(f"  5-Fold CV MedAE: {cv_medae:.2f}s (±{cv_std:.2f})")
        print(f"  Test MedAE: {medae:.2f}s")
        print(f"  Test MAE: {mae:.2f}s")
        print(f"  Test MSE: {mse:.2f}")
        print(f"  Test R²: {r2:.3f}")
        print(f"  Test MAPE: {mape:.1f}%")

        # Check for overfitting: CV score should be close to test score
        if medae > 0 and cv_medae > 0:
            overfit_gap = abs(medae - cv_medae)
            overfit_pct = (overfit_gap / cv_medae) * 100
            if overfit_pct > 20:
                print(f"  ⚠️  Overfitting detected (CV={cv_medae:.2f}s vs Test={medae:.2f}s, gap={overfit_pct:.1f}%)")
            else:
                print(f"  ✓ No overfitting (CV={cv_medae:.2f}s vs Test={medae:.2f}s, gap={overfit_pct:.1f}%)")

        # Select best model based on cross-validation MedAE (lower is better)
        if cv_medae < best_cv_score:
            best_cv_score = cv_medae
            best_model_name = name
            best_pipeline = best_estimator
            best_metrics = {
                'mse': mse,
                'mae': mae,
                'medae': medae,
                'r2': r2,
                'mape': mape,
                'cv_medae_mean': cv_medae,
                'cv_medae_std': cv_std,
                'best_params': grid_search.best_params_
            }

    print(f"\n{'='*60}")
    print(f"✓ Best model: {best_model_name} (selected by Median Absolute Error)")
    print(f"  Tuned params: {best_metrics['best_params']}")
    print(f"  Cross-Val MedAE: {best_metrics['cv_medae_mean']:.2f}s (±{best_metrics['cv_medae_std']:.2f})")
    print(f"  Test MedAE: {best_metrics['medae']:.2f}s")
    print(f"  Test MAE: {best_metrics['mae']:.2f}s")
    print(f"  Test R²: {best_metrics['r2']:.3f}")
    print(f"  Test MAPE: {best_metrics['mape']:.1f}%")
    print(f"{'='*60}\n")

    # Save model to S3 with versioning
    save_model_to_s3(best_pipeline, best_metrics, len(df), X.columns)

    # Analyze feature importance if available
    analyze_feature_importance(best_pipeline, X.columns)

    return True

def analyze_feature_importance(pipeline, feature_names):
    """Analyze and display feature importance"""
    try:
        regressor = pipeline.named_steps['regressor']

        if hasattr(regressor, 'feature_importances_'):
            # Get feature names after preprocessing
            preprocessor = pipeline.named_steps['preprocessor']

            # Get categorical feature names after one-hot encoding
            cat_encoder = preprocessor.named_transformers_['cat']
            cat_feature_names = cat_encoder.get_feature_names_out(CATEGORICAL_FEATURES)

            # Combine all feature names
            all_feature_names = list(cat_feature_names) + NUMERICAL_FEATURES + BOOLEAN_FEATURES

            # Get importances
            importances = regressor.feature_importances_

            # Create DataFrame
            importance_df = pd.DataFrame({
                'feature': all_feature_names,
                'importance': importances
            }).sort_values('importance', ascending=False)

            print("Feature Importance (Top 15):")
            print("="*50)
            for idx, row in importance_df.head(15).iterrows():
                bar_length = int(row['importance'] * 50)
                bar = '█' * bar_length
                print(f"{row['feature']:30s} {bar} {row['importance']:.4f}")
            print()

            return importance_df
    except Exception as e:
        print(f"Could not analyze feature importance: {e}")
        return None

def should_retrain_model(model_path="best_model.pkl", max_age_days=1):
    """
    DEPRECATED: This function is no longer used.
    Model retraining is now handled by the daily scheduler in app.py (3 AM daily).
    Kept for backward compatibility but always returns False.
    """
    return False  # Retraining is handled by scheduler, not on-demand

def save_model_to_s3(pipeline, metrics, training_samples, feature_columns):
    """
    Save trained model to S3 with versioning and metadata.
    Creates a new version on each training run.
    """
    from utils.storage.s3_storage import S3Storage
    from datetime import datetime

    try:
        s3 = S3Storage()

        # Generate version identifier
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        version = f"v2.0_{timestamp}"

        # Serialize model
        model_bytes = joblib.dumps(pipeline)

        # Prepare metadata
        metadata = {
            'version': version,
            'timestamp': timestamp,
            'model_name': 'eta_estimator',
            'metrics': {
                'medae': float(metrics['medae']),
                'mae': float(metrics['mae']),
                'mse': float(metrics['mse']),
                'r2_score': float(metrics['r2']),
                'mape': float(metrics['mape']),
                'cv_medae_mean': float(metrics['cv_medae_mean']),
                'cv_medae_std': float(metrics['cv_medae_std'])
            },
            'training_info': {
                'samples': training_samples,
                'features': list(feature_columns),
                'categorical_features': CATEGORICAL_FEATURES,
                'numerical_features': NUMERICAL_FEATURES,
                'boolean_features': BOOLEAN_FEATURES
            },
            'best_params': metrics.get('best_params', {})
        }

        # Save model binary to S3
        model_key = f"{_S3_MODEL_PREFIX}/{version}/model.pkl"
        s3.client.put_object(
            Bucket=s3.bucket_name,
            Key=model_key,
            Body=model_bytes
        )

        # Save metadata as JSON
        metadata_key = f"{_S3_MODEL_PREFIX}/{version}/metadata.json"
        s3.client.put_object(
            Bucket=s3.bucket_name,
            Key=metadata_key,
            Body=json.dumps(metadata, indent=2)
        )

        # Update "latest" pointer to this version
        latest_key = f"{_S3_MODEL_PREFIX}/latest.txt"
        s3.client.put_object(
            Bucket=s3.bucket_name,
            Key=latest_key,
            Body=version
        )

        log_with_context(
            logger, 'info', f'✅ Model saved to S3: {version}',
            version=version,
            medae=metrics['medae'],
            training_samples=training_samples,
            s3_key=model_key
        )

        print(f"✓ Model saved to S3: s3://{s3.bucket_name}/{model_key}")
        print(f"✓ Version: {version}")
        print(f"✓ Metadata: s3://{s3.bucket_name}/{metadata_key}")

        return version

    except Exception as e:
        log_with_context(
            logger, 'error', f'Failed to save model to S3: {str(e)}',
            error_type=type(e).__name__
        )
        # Fallback: save locally
        print(f"⚠️  S3 save failed, saving locally as backup: {e}")
        local_path = "best_model.pkl"
        joblib.dump(pipeline, local_path)
        print(f"✓ Fallback: Model saved to {local_path}")
        return None

def get_latest_model_version_from_s3():
    """
    Get the latest model version from S3.
    Returns None if not found or on error.
    """
    from utils.storage.s3_storage import S3Storage

    try:
        s3 = S3Storage()
        latest_key = f"{_S3_MODEL_PREFIX}/latest.txt"

        response = s3.client.get_object(
            Bucket=s3.bucket_name,
            Key=latest_key
        )

        version = response['Body'].read().decode('utf-8').strip()
        return version

    except Exception as e:
        log_with_context(
            logger, 'warning', f'Could not get latest model version from S3: {str(e)}',
            error_type=type(e).__name__
        )
        return None

def download_model_from_s3(version):
    """
    Download model from S3 and cache it locally.
    Returns local path to cached model.
    """
    from utils.storage.s3_storage import S3Storage
    from pathlib import Path

    try:
        s3 = S3Storage()

        # Create local cache directory
        cache_dir = Path(_LOCAL_CACHE_DIR) / version
        cache_dir.mkdir(parents=True, exist_ok=True)

        local_model_path = cache_dir / "model.pkl"

        # Download model from S3
        model_key = f"{_S3_MODEL_PREFIX}/{version}/model.pkl"

        response = s3.client.get_object(
            Bucket=s3.bucket_name,
            Key=model_key
        )

        model_bytes = response['Body'].read()

        # Save to local cache
        with open(local_model_path, 'wb') as f:
            f.write(model_bytes)

        log_with_context(
            logger, 'info', f'📥 Downloaded model from S3 to local cache',
            version=version,
            s3_key=model_key,
            local_path=str(local_model_path)
        )

        return str(local_model_path)

    except Exception as e:
        log_with_context(
            logger, 'error', f'Failed to download model from S3: {str(e)}',
            version=version,
            error_type=type(e).__name__
        )
        return None

def prepare_job_features(conversion_job: ConversionJob) -> pd.DataFrame:
    """
    Extract all available features from a conversion job for prediction.
    Uses only features that are known BEFORE processing starts.
    """
    # Extract file extension
    input_extension = os.path.splitext(conversion_job.input_filename)[1].lower() if conversion_job.input_filename else 'unknown'

    # Prepare feature dictionary
    features = {
        # Categorical features
        'device_profile': conversion_job.device_profile,
        'input_extension': input_extension,
        'output_format': conversion_job.output_format or 'mobi',

        # Numerical features
        'input_file_size': conversion_job.input_file_size,
        'cropping': conversion_job.cropping or 0,
        'splitter': conversion_job.splitter or 0,
        'custom_width': conversion_job.custom_width or 0,
        'custom_height': conversion_job.custom_height or 0,

        # Boolean features (convert to int 0/1)
        'upscale': int(conversion_job.upscale or False),
        'force_color': int(conversion_job.force_color or False),
        'autolevel': int(conversion_job.autolevel or False),
        'force_png': int(conversion_job.force_png or False),
        'mozjpeg': int(conversion_job.mozjpeg or False),
        'hq': int(conversion_job.hq or False),
        'manga_style': int(conversion_job.manga_style or False),
        'two_panel': int(conversion_job.two_panel or False),
    }

    return pd.DataFrame([features])

def load_model_cached():
    """
    Load ML model with triple-tier caching and S3 versioning.

    Tier 1: Memory cache (_CACHED_MODEL) - instant access
    Tier 2: Local disk cache (/tmp/ml_models/{version}/) - fast access
    Tier 3: S3 storage (ml_models/eta_estimator/{version}/) - persistent

    Automatically detects and loads new versions when model is retrained.
    This handles the daily retraining updates seamlessly.
    """
    global _CACHED_MODEL, _CACHED_MODEL_VERSION
    from pathlib import Path

    try:
        # Get latest version from S3
        latest_version = get_latest_model_version_from_s3()

        if latest_version is None:
            # Fallback to local file if S3 is unavailable
            log_with_context(logger, 'warning', 'S3 unavailable, checking for local fallback model')
            fallback_path = "best_model.pkl"
            if os.path.exists(fallback_path):
                if _CACHED_MODEL is None:
                    _CACHED_MODEL = joblib.load(fallback_path)
                    _CACHED_MODEL_VERSION = "local_fallback"
                    log_with_context(logger, 'info', '✅ Loaded fallback model from local file')
                return _CACHED_MODEL
            else:
                raise FileNotFoundError("No model available (S3 unavailable and no local fallback)")

        # Tier 1: Check memory cache
        if _CACHED_MODEL is not None and _CACHED_MODEL_VERSION == latest_version:
            # Model is cached in memory and up-to-date
            return _CACHED_MODEL

        # Version changed! Need to reload
        if _CACHED_MODEL_VERSION is not None and _CACHED_MODEL_VERSION != latest_version:
            log_with_context(
                logger, 'info', f'🔄 New model version detected: {_CACHED_MODEL_VERSION} → {latest_version}',
                old_version=_CACHED_MODEL_VERSION,
                new_version=latest_version
            )

        # Tier 2: Check local disk cache
        cache_dir = Path(_LOCAL_CACHE_DIR) / latest_version
        local_model_path = cache_dir / "model.pkl"

        if local_model_path.exists():
            # Load from local cache
            log_with_context(
                logger, 'info', f'📂 Loading model from local cache',
                version=latest_version,
                path=str(local_model_path)
            )
            start_time = time.time()

            _CACHED_MODEL = joblib.load(str(local_model_path))
            _CACHED_MODEL_VERSION = latest_version

            load_duration = time.time() - start_time
            log_with_context(
                logger, 'info', f'✅ Model loaded from cache in {load_duration:.2f}s',
                version=latest_version,
                load_duration_seconds=load_duration
            )

            return _CACHED_MODEL

        # Tier 3: Download from S3 and cache locally
        log_with_context(
            logger, 'info', f'📥 Model not in cache, downloading from S3',
            version=latest_version
        )
        start_time = time.time()

        local_path = download_model_from_s3(latest_version)

        if local_path is None:
            raise Exception(f"Failed to download model version {latest_version} from S3")

        # Load into memory
        _CACHED_MODEL = joblib.load(local_path)
        _CACHED_MODEL_VERSION = latest_version

        load_duration = time.time() - start_time
        log_with_context(
            logger, 'info', f'✅ Model downloaded and loaded in {load_duration:.2f}s',
            version=latest_version,
            load_duration_seconds=load_duration
        )

        return _CACHED_MODEL

    except Exception as e:
        log_with_context(
            logger, 'error', f'Failed to load model: {str(e)}',
            error_type=type(e).__name__
        )
        # If we have a cached model (even if old version), use it
        if _CACHED_MODEL is not None:
            log_with_context(
                logger, 'warning', f'Using stale cached model version {_CACHED_MODEL_VERSION}'
            )
            return _CACHED_MODEL

        raise

def estimate_eta(conversion_job: ConversionJob, output_file_size: Optional[int] = None) -> float:
    """
    Estimate the conversion time (ETA) for a given job using v2.0 optimized model.
    Uses S3-backed triple-tier caching with automatic version detection.

    Automatically picks up new model versions after daily retraining.

    NOTE: output_file_size parameter is deprecated and ignored.
    """
    try:
        # Load cached model (auto-detects new versions from S3)
        loaded_model = load_model_cached()

        # Prepare features (no more guessing output_file_size!)
        features_df = prepare_job_features(conversion_job)

        # Make prediction
        eta = loaded_model.predict(features_df)[0]

        # Convert numpy type to Python float for JSON serialization
        eta_float = float(eta)

        log_with_context(
            logger, 'info', 'Successfully estimated ETA (v2.0)',
            job_id=conversion_job.id,
            user_id=conversion_job.session_key,
            estimated_eta=eta_float,
            input_extension=features_df['input_extension'].iloc[0],
            has_upscale=bool(features_df['upscale'].iloc[0]),
            has_autolevel=bool(features_df['autolevel'].iloc[0])
        )

        return int(round(max(0.0, eta_float)))

    except FileNotFoundError:
        log_with_context(
            logger, 'warning', 'ML model not found - using fallback heuristic',
            job_id=conversion_job.id,
            user_id=conversion_job.session_key
        )
        # Fallback heuristic
        base_estimate = conversion_job.input_file_size / 50000
        if conversion_job.input_filename and conversion_job.input_filename.lower().endswith('.pdf'):
            base_estimate *= 2.5
        return int(round(base_estimate))

    except Exception as e:
        log_with_context(
            logger, 'error', f'An error occurred during ETA estimation (v2.0): {e}',
            job_id=conversion_job.id,
            user_id=conversion_job.session_key,
            error_type=type(e).__name__
        )
        # Fallback heuristic in case of any error
        base_estimate = conversion_job.input_file_size / 50000
        if conversion_job.input_filename and conversion_job.input_filename.lower().endswith('.pdf'):
            base_estimate *= 2.5
        return int(round(base_estimate))

if __name__ == "__main__":
    train_model()
