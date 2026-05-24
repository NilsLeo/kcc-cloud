<script setup lang="ts">
import { ref, computed, nextTick } from 'vue';
import Icon from '@/components/Icon.vue';
import Button from '@/components/ui/Button.vue';
import SubscriptionCard from '@/components/SubscriptionCard.vue';
import type { Subscription } from '@/components/SubscriptionCard.vue';
import SupportEmailCard from '@/components/SupportEmailCard.vue';

const props = defineProps<{
  totals: { conversions: number; downloads: number };
  userEmail: string;
  userName: string;
  jobs?: Array<{ id: string; label: string; sub?: string }>;
  subscription?: Subscription;
}>();

const emit = defineEmits<{
  'update:userEmail': [v: string];
  'update:userName': [v: string];
  'cancel-plan': [];
  'sign-out': [];
}>();

const editingName = ref(false);
const tempName = ref('');
const editingEmail = ref(false);
const tempEmail = ref('');
const nameInput = ref<HTMLInputElement | null>(null);
const emailInput = ref<HTMLInputElement | null>(null);

const initials = computed(() =>
  (props.userName || 'A').split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()
);

function startEditName() {
  tempName.value = props.userName;
  editingName.value = true;
  nextTick(() => nameInput.value?.focus());
}
function saveName() {
  if (tempName.value.trim()) emit('update:userName', tempName.value.trim());
  editingName.value = false;
}
function startEditEmail() {
  tempEmail.value = props.userEmail;
  editingEmail.value = true;
  nextTick(() => emailInput.value?.focus());
}
function saveEmail() {
  const v = tempEmail.value.trim();
  if (v && /\S+@\S+\.\S+/.test(v)) emit('update:userEmail', v);
  editingEmail.value = false;
}
</script>

<template>
  <div class="space-y-6 animate-slide-up max-w-3xl">
    <!-- header -->
    <div class="flex items-end justify-between gap-3">
      <div>
        <h2 class="text-2xl md:text-3xl font-bold font-poppins tracking-tight">Account</h2>
        <p class="text-muted-foreground mt-1">Profile, subscription, and support.</p>
      </div>
      <Button variant="outline" size="sm" @click="$emit('sign-out')">
        <Icon name="x" class="h-3.5 w-3.5" /> Sign out
      </Button>
    </div>

    <!-- profile card -->
    <div class="rounded-lg border bg-card overflow-hidden">
      <div class="p-5 flex items-center gap-4 border-b">
        <div class="h-14 w-14 rounded-full bg-muted text-foreground grid place-items-center font-poppins font-semibold text-lg border">
          {{ initials }}
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 flex-wrap">
            <template v-if="editingName">
              <input
                ref="nameInput"
                v-model="tempName"
                class="font-poppins font-semibold text-lg bg-background border border-input rounded-md px-2 py-0.5 outline-none focus:ring-2 focus:ring-theme-medium/40"
                @keydown.enter="saveName"
                @blur="saveName"
                @keydown.esc="editingName = false"
              />
            </template>
            <template v-else>
              <h3 class="font-poppins font-semibold text-lg">{{ userName }}</h3>
              <Button variant="ghost" size="icon" class="h-8 w-8 text-muted-foreground hover:text-foreground" @click="startEditName">
                <Icon name="edit" class="h-3.5 w-3.5" />
              </Button>
            </template>
          </div>
          <div class="flex items-center gap-1 text-sm text-muted-foreground">
            <template v-if="editingEmail">
              <input
                ref="emailInput"
                v-model="tempEmail"
                type="email"
                class="text-sm bg-background border border-input rounded-md px-2 py-0.5 outline-none focus:ring-2 focus:ring-theme-medium/40"
                @keydown.enter="saveEmail"
                @blur="saveEmail"
                @keydown.esc="editingEmail = false"
              />
            </template>
            <template v-else>
              <span>{{ userEmail }}</span>
              <Button variant="ghost" size="icon" class="h-7 w-7 text-muted-foreground hover:text-foreground" @click="startEditEmail">
                <Icon name="edit" class="h-3 w-3" />
              </Button>
            </template>
          </div>
          <p class="text-xs text-muted-foreground mt-0.5">Member since March 2025</p>
        </div>
      </div>
      <div class="p-5 grid grid-cols-2 gap-4 text-center">
        <div>
          <div class="text-2xl font-bold font-poppins">{{ totals.conversions }}</div>
          <div class="text-xs text-muted-foreground mt-0.5">Conversions</div>
        </div>
        <div class="border-l">
          <div class="text-2xl font-bold font-poppins">{{ totals.downloads }}</div>
          <div class="text-xs text-muted-foreground mt-0.5">Downloads</div>
        </div>
      </div>
    </div>

    <!-- subscription -->
    <SubscriptionCard :subscription="subscription" @cancel-plan="$emit('cancel-plan')" />

    <!-- support -->
    <SupportEmailCard :user-email="userEmail" :jobs="jobs" />

    <!-- danger zone -->
    <div class="rounded-lg border border-destructive/30 overflow-hidden">
      <div class="p-5 flex items-center justify-between gap-3">
        <div>
          <h3 class="font-poppins font-semibold text-sm">Delete account</h3>
          <p class="text-xs text-muted-foreground mt-0.5">Permanently remove your account, billing data and all download history.</p>
        </div>
        <Button variant="outline" size="sm" class="text-destructive hover:text-destructive border-destructive/30">Delete</Button>
      </div>
    </div>
  </div>
</template>
