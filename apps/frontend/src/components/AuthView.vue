<script setup lang="ts">
import { ref } from 'vue';
import Icon from '@/components/Icon.vue';
import Button from '@/components/ui/Button.vue';

const props = defineProps<{ initialMode?: 'login' | 'register' | 'forgot' }>();
const emit = defineEmits<{ authenticated: [payload: { email: string; name: string }] }>();

const mode = ref<'login' | 'register' | 'forgot'>(props.initialMode || 'login');
const email = ref('');
const password = ref('');
const confirm = ref('');
const name = ref('');
const acceptToc = ref(false);
const submitting = ref(false);
const error = ref('');
const sentReset = ref(false);

function submit() {
  error.value = '';
  if (mode.value === 'register') {
    if (password.value !== confirm.value) { error.value = 'Passwords do not match.'; return; }
    if (!acceptToc.value) { error.value = 'Please accept the terms and the privacy policy.'; return; }
  }
  submitting.value = true;
  setTimeout(() => {
    submitting.value = false;
    if (mode.value === 'forgot') { sentReset.value = true; return; }
    emit('authenticated', { email: email.value, name: name.value || email.value.split('@')[0] });
  }, 700);
}
</script>

<template>
  <div class="max-w-md mx-auto animate-slide-up">
    <div class="rounded-lg border bg-card overflow-hidden">
      <div class="p-6 border-b">
        <h2 class="font-poppins font-semibold text-xl tracking-tight">
          {{ mode === 'login' ? 'Sign in' : mode === 'register' ? 'Create an account' : 'Reset password' }}
        </h2>
        <p class="text-sm text-muted-foreground mt-1">
          <template v-if="mode === 'login'">Welcome back.</template>
          <template v-else-if="mode === 'register'">Free, no credit card.</template>
          <template v-else>We'll email you a reset link.</template>
        </p>
      </div>

      <form class="p-6 space-y-3" @submit.prevent="submit">
        <div v-if="mode === 'register'" class="space-y-1.5">
          <label class="text-xs font-medium">Name</label>
          <input v-model="name" required class="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-theme-medium/40" />
        </div>
        <div class="space-y-1.5">
          <label class="text-xs font-medium">Email</label>
          <input v-model="email" type="email" required class="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-theme-medium/40" />
        </div>
        <div v-if="mode !== 'forgot'" class="space-y-1.5">
          <div class="flex justify-between items-baseline">
            <label class="text-xs font-medium">Password</label>
            <button v-if="mode === 'login'" type="button" class="text-xs text-muted-foreground hover:text-foreground" @click="mode = 'forgot'">Forgot?</button>
          </div>
          <input v-model="password" type="password" required minlength="8" class="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-theme-medium/40" />
        </div>
        <div v-if="mode === 'register'" class="space-y-1.5">
          <label class="text-xs font-medium">Confirm password</label>
          <input v-model="confirm" type="password" required class="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-theme-medium/40" />
        </div>
        <label v-if="mode === 'register'" class="flex items-start gap-2 text-xs text-muted-foreground pt-1 cursor-pointer">
          <input v-model="acceptToc" type="checkbox" class="mt-0.5 accent-theme-medium" />
          <span>I accept the <a href="#" class="text-theme-medium hover:underline">Terms</a> and have read the <a href="#" class="text-theme-medium hover:underline">Privacy policy</a>.</span>
        </label>

        <div v-if="error" class="text-xs text-destructive bg-destructive/5 border border-destructive/30 rounded-md p-2">{{ error }}</div>
        <div v-if="sentReset" class="text-xs text-success bg-success/5 border border-success/30 rounded-md p-2">
          If an account exists for {{ email }}, a reset link is on its way.
        </div>

        <Button variant="brand" size="lg" type="submit" :disabled="submitting" class="w-full">
          <Icon v-if="submitting" name="loader" class="h-4 w-4 animate-spin" />
          <span v-if="submitting">Please wait…</span>
          <span v-else-if="mode === 'login'">Sign in</span>
          <span v-else-if="mode === 'register'">Create account</span>
          <span v-else>Send reset link</span>
        </Button>

        <div class="text-center text-xs text-muted-foreground pt-2">
          <template v-if="mode === 'login'">
            New here?
            <button type="button" class="text-theme-medium hover:underline font-medium" @click="mode = 'register'">Create an account</button>
          </template>
          <template v-else-if="mode === 'register'">
            Already have an account?
            <button type="button" class="text-theme-medium hover:underline font-medium" @click="mode = 'login'">Sign in</button>
          </template>
          <template v-else>
            <button type="button" class="text-theme-medium hover:underline font-medium" @click="mode = 'login'">← Back to sign in</button>
          </template>
        </div>
      </form>
    </div>
  </div>
</template>
