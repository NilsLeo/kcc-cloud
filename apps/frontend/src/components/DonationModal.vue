<script setup lang="ts">
import { ref, watch } from 'vue';
import Icon from '@/components/Icon.vue';
import Button from '@/components/ui/Button.vue';
import Badge from '@/components/ui/Badge.vue';

const props = defineProps<{
  open: boolean;
  fileName?: string | null;
}>();

const emit = defineEmits<{
  close: [];
  donate: [];
  skip: [];
}>();

const step = ref<'pitch' | 'pay' | 'success'>('pitch');
const card = ref('4242 4242 4242 4242');
const exp = ref('12 / 28');
const cvc = ref('123');
const processing = ref(false);

watch(() => props.open, (v) => {
  if (v) { step.value = 'pitch'; processing.value = false; }
});

function pay() {
  processing.value = true;
  setTimeout(() => { processing.value = false; step.value = 'success'; }, 1100);
}
function finish() {
  emit('donate');
  emit('close');
}
</script>

<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center p-4"
    role="dialog"
    aria-modal="true"
  >
    <div class="absolute inset-0 bg-foreground/40 backdrop-blur-sm" @click="$emit('skip')" />
    <div class="relative w-full max-w-md bg-card border rounded-xl shadow-xl overflow-hidden animate-slide-up">
      <button class="absolute top-3 right-3 text-muted-foreground hover:text-foreground z-10" aria-label="Close" @click="$emit('skip')">
        <Icon name="x" class="h-4 w-4" />
      </button>

      <!-- pitch step -->
      <div v-if="step === 'pitch'">
        <div class="p-6 pb-4 bg-gradient-to-br from-theme-medium/10 to-rose-500/10">
          <div class="flex items-center gap-2 mb-2">
            <Icon name="heart" class="h-4 w-4 text-rose-500" />
            <Badge variant="purple">Optional</Badge>
          </div>
          <h3 class="font-poppins font-bold text-xl tracking-tight">Support the project</h3>
          <p class="text-sm text-muted-foreground mt-1 leading-relaxed">
            Your file is ready! Conversions are free — but $1.99/month keeps the servers running.
          </p>
        </div>
        <div class="p-6 pt-4 space-y-4">
          <div class="flex items-baseline justify-center gap-1">
            <span class="text-4xl font-bold font-poppins tracking-tight">$1.99</span>
            <span class="text-muted-foreground text-sm">/ month</span>
          </div>
          <ul class="text-sm space-y-1.5">
            <li class="flex items-start gap-2">
              <Icon name="check" class="h-4 w-4 text-success mt-0.5 shrink-0" />
              <span>Keeps the servers paid for</span>
            </li>
            <li class="flex items-start gap-2">
              <Icon name="check" class="h-4 w-4 text-success mt-0.5 shrink-0" />
              <span>Skip this prompt forever</span>
            </li>
            <li class="flex items-start gap-2">
              <Icon name="check" class="h-4 w-4 text-success mt-0.5 shrink-0" />
              <span>Cancel anytime, no questions</span>
            </li>
          </ul>
          <div class="space-y-2 pt-2">
            <Button variant="brand" size="lg" class="w-full" @click="step = 'pay'">
              <Icon name="heart" class="h-4 w-4" /> Subscribe $1.99/mo &amp; download
            </Button>
            <Button variant="ghost" size="default" class="w-full text-muted-foreground" @click="$emit('skip')">
              Continue without subscribing
            </Button>
          </div>
          <p class="text-[11px] text-center text-muted-foreground">
            Powered by <span class="font-medium text-foreground">Stripe</span> · Secure payment
          </p>
        </div>
      </div>

      <!-- pay step -->
      <div v-else-if="step === 'pay'">
        <div class="p-6 pb-3 border-b">
          <button class="text-xs text-muted-foreground hover:text-foreground mb-2 inline-flex items-center gap-1" @click="step = 'pitch'">← Back</button>
          <h3 class="font-poppins font-bold text-lg">Payment details</h3>
          <p class="text-sm text-muted-foreground mt-1">$1.99 / month · Cancel anytime</p>
        </div>
        <div class="p-6 space-y-3">
          <div class="space-y-1.5">
            <label class="text-xs font-medium">Card number</label>
            <div class="relative">
              <input
                v-model="card"
                class="w-full h-10 rounded-md border border-input bg-background px-3 pr-12 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-theme-medium/40"
              />
              <span class="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] font-bold tracking-wider text-blue-700 dark:text-blue-300 px-1 py-0.5 rounded bg-blue-50 dark:bg-blue-950">VISA</span>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div class="space-y-1.5">
              <label class="text-xs font-medium">Expiration</label>
              <input v-model="exp" class="w-full h-10 rounded-md border border-input bg-background px-3 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-theme-medium/40" />
            </div>
            <div class="space-y-1.5">
              <label class="text-xs font-medium">CVC</label>
              <input v-model="cvc" class="w-full h-10 rounded-md border border-input bg-background px-3 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-theme-medium/40" />
            </div>
          </div>
          <div class="flex items-center justify-between p-3 rounded-md bg-muted/50 text-sm">
            <span>Monthly total</span>
            <span class="font-mono font-semibold">$1.99 USD</span>
          </div>
          <Button variant="brand" size="lg" class="w-full" :disabled="processing" @click="pay">
            <Icon v-if="processing" name="loader" class="h-4 w-4 animate-spin" />
            <span v-if="processing">Processing…</span>
            <span v-else>Pay &amp; download</span>
          </Button>
          <p class="text-[11px] text-center text-muted-foreground inline-flex items-center justify-center gap-1.5 w-full">
            <Icon name="check" class="h-3 w-3" /> Secured by Stripe · 256-bit TLS
          </p>
        </div>
      </div>

      <!-- success step -->
      <div v-else>
        <div class="p-8 text-center">
          <div class="mx-auto mb-3 rounded-full bg-success/15 text-success p-3 w-fit">
            <Icon name="checkCircle" class="h-8 w-8" />
          </div>
          <h3 class="font-poppins font-bold text-xl">Thank you!</h3>
          <p class="text-sm text-muted-foreground mt-1">You're now a supporter. We'll skip this prompt from now on.</p>
          <Button variant="brand" size="lg" class="w-full mt-5" @click="finish">
            <Icon name="download" class="h-4 w-4" /> Download {{ fileName || 'your file' }}
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>
