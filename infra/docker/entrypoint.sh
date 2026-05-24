#!/bin/sh
set -e

# Ensure data directories exist
mkdir -p /data/files/input /data/files/output

# Write the api startup wrapper (waits for redis, runs prisma migrate, then starts)
cat > /entrypoint-api.sh << 'EOF'
#!/bin/sh
# Wait for redis
until redis-cli -u "${REDIS_URL:-redis://localhost:6379}" ping 2>/dev/null | grep -q PONG; do
  echo "api: waiting for redis..."
  sleep 1
done

# Run prisma migration
cd /app && /app/node_modules/.bin/prisma db push \
  --schema /app/packages/db/prisma/base/schema.prisma \
  --skip-generate 2>&1 | grep -v "^$" || true

exec node /app/apps/api/dist/main
EOF
chmod +x /entrypoint-api.sh

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/mgc.conf
