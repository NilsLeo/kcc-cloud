<script setup lang="ts">
import { computed } from 'vue';
import Icon from '@/components/Icon.vue';
import Button from '@/components/ui/Button.vue';
import Badge from '@/components/ui/Badge.vue';

export interface Subscription {
  name: string;
  price: number;
  currency: string;
  renewsOn?: string;
  status: 'active' | 'canceling';
  fileLimit?: number | null;
  invoices?: Array<{ id: string; date: string; amount: number; status: string }>;
}

const props = defineProps<{ subscription?: Subscription }>();
const emit = defineEmits<{ 'cancel-plan': []; 'change-plan': []; 'update-payment': [] }>();

const plan = computed(() => props.subscription || { name: 'Free', price: 0, currency: 'EUR', renewsOn: null, status: 'active' as const, fileLimit: 5, invoices: [] });
const paid = computed(() => plan.value.price > 0);
</script>

<template>
  <div class="rounded-lg border bg-card overflow-hidden">
    <div class="p-5 border-b flex items-start justify-between gap-4 flex-wrap">
      <div class="flex items-start gap-3">
        <div class="rounded-md bg-theme-medium/10 p-2 text-theme-medium">
          <Icon name="sparkles" class="h-5 w-5" />
        </div>
        <div>
          <div class="flex items-center gap-2 flex-wrap">
            <h3 class="font-poppins font-semibold">{{ plan.name }} plan</h3>
            <Badge :variant="plan.status === 'active' ? 'success' : 'warn'">{{ plan.status === 'active' ? 'Active' : plan.status }}</Badge>
          </div>
          <p class="text-sm text-muted-foreground mt-0.5">
            <template v-if="paid">
              €{{ plan.price.toFixed(2) }} / month ·
              <template v-if="plan.status === 'canceling'">Ends</template>
              <template v-else>Renews</template>
              {{ plan.renewsOn }}
            </template>
            <template v-else>
              Free for personal use. Limited to {{ plan.fileLimit || 5 }} files per day.
            </template>
          </p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <Button variant="outline" size="sm" @click="$emit('change-plan')">{{ paid ? 'Change plan' : 'Upgrade' }}</Button>
        <Button v-if="paid && plan.status === 'active'" variant="ghost" size="sm" class="text-destructive hover:text-destructive" @click="$emit('cancel-plan')">Cancel</Button>
      </div>
    </div>

    <div class="p-5 grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
      <div>
        <div class="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Payment method</div>
        <div v-if="paid" class="flex items-center gap-2.5 p-2.5 rounded-md border bg-muted/30">
          <span class="text-[10px] font-bold tracking-wider px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300">VISA</span>
          <div class="flex-1">
            <div class="font-mono">•••• •••• •••• 4242</div>
            <div class="text-xs text-muted-foreground">Expires 12/28</div>
          </div>
          <Button variant="ghost" size="icon" class="h-8 w-8 text-muted-foreground hover:text-foreground" @click="$emit('update-payment')">
            <Icon name="edit" class="h-3.5 w-3.5" />
          </Button>
        </div>
        <div v-else class="p-2.5 rounded-md border bg-muted/30 text-muted-foreground italic text-xs">No payment method on file.</div>
      </div>
      <div>
        <div class="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Billing address</div>
        <div class="p-2.5 rounded-md border bg-muted/30 text-xs leading-relaxed">
          <template v-if="paid">
            Alex Chen<br />Musterstraße 12<br />10115 Berlin<br />Germany
          </template>
          <template v-else>
            <span class="text-muted-foreground italic">Not provided yet</span>
          </template>
        </div>
      </div>
    </div>

    <div v-if="paid && plan.invoices?.length" class="border-t">
      <div class="p-5 pb-3">
        <div class="text-xs font-medium text-muted-foreground uppercase tracking-wider">Invoices</div>
      </div>
      <div class="divide-y">
        <div v-for="inv in plan.invoices" :key="inv.id" class="px-5 py-3 flex items-center justify-between text-sm">
          <div>
            <div class="font-medium">{{ inv.date }}</div>
            <div class="text-xs text-muted-foreground">#{{ inv.id }}</div>
          </div>
          <div class="flex items-center gap-3">
            <span class="font-mono">€{{ inv.amount.toFixed(2) }}</span>
            <Badge :variant="inv.status === 'paid' ? 'success' : 'warn'">{{ inv.status }}</Badge>
            <a href="#" class="text-xs text-theme-medium hover:underline">PDF</a>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
