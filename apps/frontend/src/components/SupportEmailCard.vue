<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import Icon from '@/components/Icon.vue';
import Button from '@/components/ui/Button.vue';
import Badge from '@/components/ui/Badge.vue';

const props = defineProps<{
  userEmail?: string;
  jobs?: Array<{ id: string; label: string; sub?: string }>;
}>();

const open = ref(false);
const email = 'support@mangaconverter.com';
const copied = ref(false);
const sent = ref(false);
const fromEmail = ref(props.userEmail || '');
const subject = ref('');
const body = ref('');
const selectedJob = ref<{ id: string; label: string; sub?: string } | null>(null);
const jobQuery = ref('');
const jobOpen = ref(false);
const sending = ref(false);

watch(() => props.userEmail, (v) => { if (v && !fromEmail.value) fromEmail.value = v; });

const allJobs = computed(() => props.jobs || []);
const filteredJobs = computed(() => {
  const q = jobQuery.value.trim().toLowerCase();
  if (!q) return allJobs.value.slice(0, 8);
  return allJobs.value.filter(j => j.label.toLowerCase().includes(q) || j.id.toLowerCase().includes(q)).slice(0, 8);
});

function selectJob(j: { id: string; label: string; sub?: string }) {
  selectedJob.value = j;
  jobQuery.value = '';
  jobOpen.value = false;
}
function clearJob() {
  selectedJob.value = null;
  jobQuery.value = '';
}
function copy() {
  navigator.clipboard?.writeText(email);
  copied.value = true;
  setTimeout(() => (copied.value = false), 1500);
}
function send() {
  sending.value = true;
  setTimeout(() => {
    sending.value = false;
    sent.value = true;
    subject.value = '';
    body.value = '';
    selectedJob.value = null;
    jobQuery.value = '';
  }, 900);
}
</script>

<template>
  <div class="rounded-lg border bg-card overflow-hidden">
    <button type="button" class="w-full p-4 flex items-center gap-3 hover:bg-muted/30 transition-colors text-left" @click="open = !open">
      <div class="rounded-md bg-theme-medium/15 p-2 text-theme-medium shrink-0">
        <Icon name="mail" class="h-4 w-4" />
      </div>
      <div class="flex-1 min-w-0">
        <h3 class="font-poppins font-medium text-sm">Contact support</h3>
        <p class="text-xs text-muted-foreground">Reply within one business day.</p>
      </div>
      <Icon name="chevronDown" :class="['h-4 w-4 text-muted-foreground transition-transform shrink-0', open && 'rotate-180']" />
    </button>

    <div v-if="open" class="border-t animate-slide-up">
      <div class="p-5 border-b bg-muted/30">
        <div class="flex items-center gap-2">
          <div class="flex-1 min-w-0 px-3 py-2 rounded-md border bg-background font-mono text-sm truncate">{{ email }}</div>
          <Button variant="outline" size="sm" @click="copy">
            <Icon :name="copied ? 'check' : 'copy'" class="h-3.5 w-3.5" />
            {{ copied ? 'Copied' : 'Copy' }}
          </Button>
          <a
            :href="'mailto:' + email"
            class="inline-flex items-center gap-1.5 h-8 px-3 text-xs font-medium rounded-md border bg-background hover:bg-accent transition-colors"
          >
            <Icon name="mail" class="h-3.5 w-3.5" /> Email
          </a>
        </div>
      </div>

      <div class="p-5">
        <div v-if="sent" class="flex items-start gap-2 p-3 rounded-md bg-success/10 border border-success/30">
          <Icon name="checkCircle" class="h-4 w-4 text-success mt-0.5 shrink-0" />
          <div class="text-sm">
            <div class="font-medium text-foreground">Message sent</div>
            <div class="text-muted-foreground">We'll reply to your account email soon.</div>
          </div>
        </div>
        <form v-else class="space-y-3" @submit.prevent="send">
          <div class="space-y-1.5">
            <label class="text-xs font-medium flex items-center gap-1.5">
              Your email
              <span class="text-destructive">*</span>
            </label>
            <input
              v-model="fromEmail"
              type="email"
              required
              placeholder="you@example.com"
              class="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-theme-medium/40"
            />
          </div>
          <div class="space-y-1.5">
            <label class="text-xs font-medium">Subject</label>
            <input
              v-model="subject"
              required
              placeholder="e.g. Conversion failed on Kindle Paperwhite"
              class="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-theme-medium/40"
            />
          </div>
          <div class="space-y-1.5">
            <label class="text-xs font-medium flex items-center gap-1.5">
              Job
              <span class="text-[10px] font-normal text-muted-foreground">(optional)</span>
            </label>
            <!-- selected pill -->
            <div v-if="selectedJob" class="flex items-center gap-2 px-2.5 py-2 rounded-md border bg-muted/30">
              <Icon name="fileText" class="h-3.5 w-3.5 text-theme-medium shrink-0" />
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium truncate">{{ selectedJob.label }}</div>
                <div v-if="selectedJob.sub" class="text-[11px] text-muted-foreground truncate">{{ selectedJob.sub }}</div>
              </div>
              <button type="button" class="text-muted-foreground hover:text-foreground" aria-label="Clear" @click="clearJob">
                <Icon name="x" class="h-3.5 w-3.5" />
              </button>
            </div>
            <!-- searchable combobox -->
            <div v-else class="relative">
              <input
                v-model="jobQuery"
                :placeholder="allJobs.length ? 'Search jobs by filename…' : 'No recent jobs'"
                :disabled="!allJobs.length"
                class="w-full h-9 rounded-md border border-input bg-background px-3 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-theme-medium/40 disabled:opacity-60"
                @focus="jobOpen = true"
                @input="jobOpen = true"
              />
              <Icon
                name="chevronDown"
                :class="['absolute right-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground transition-transform', jobOpen && 'rotate-180']"
              />
              <template v-if="jobOpen && allJobs.length">
                <div class="fixed inset-0 z-30" @click="jobOpen = false" />
                <div class="absolute z-40 mt-1 w-full rounded-md border bg-background shadow-lg max-h-60 overflow-auto scrollbar-thin">
                  <button
                    v-for="j in filteredJobs"
                    :key="j.id"
                    type="button"
                    class="flex w-full items-start gap-2 px-3 py-2 text-left hover:bg-accent transition-colors border-b last:border-b-0"
                    @click="selectJob(j)"
                  >
                    <Icon name="fileText" class="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
                    <div class="min-w-0 flex-1">
                      <div class="text-sm truncate">{{ j.label }}</div>
                      <div v-if="j.sub" class="text-[11px] text-muted-foreground truncate">{{ j.sub }}</div>
                    </div>
                  </button>
                  <div v-if="!filteredJobs.length" class="px-3 py-3 text-xs text-muted-foreground text-center">
                    No jobs match "{{ jobQuery }}"
                  </div>
                </div>
              </template>
            </div>
          </div>
          <div class="space-y-1.5">
            <label class="text-xs font-medium">Message</label>
            <textarea
              v-model="body"
              required
              rows="4"
              placeholder="Tell us what happened…"
              class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-theme-medium/40"
            />
          </div>
          <div class="flex items-center justify-between gap-3">
            <p class="text-[11px] text-muted-foreground">Or just write to <span class="font-mono">{{ email }}</span></p>
            <Button variant="brand" size="sm" type="submit" :disabled="sending">
              <Icon v-if="sending" name="loader" class="h-3.5 w-3.5 animate-spin" />
              <Icon v-else name="send" class="h-3.5 w-3.5" />
              {{ sending ? 'Sending…' : 'Send message' }}
            </Button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
