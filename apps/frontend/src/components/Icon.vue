<script setup lang="ts">
import {
  Upload, FileUp, Download, Star, Sun, Moon, X, Check, CheckCircle2, ChevronDown,
  ChevronsRight, Loader2, Trash2, HelpCircle, Settings, Smartphone, BookOpen, Book,
  Sparkles, Plus, Clock, FileText, Archive, Image as ImageIcon, Heart, Github, Mail,
  Copy, Send, Edit, Crop, Square, User, ChevronLeft, ChevronRight, Bug,
} from 'lucide-vue-next';
import { computed } from 'vue';

const props = defineProps<{ name: string; class?: string }>();

const MAP: Record<string, any> = {
  upload: Upload, fileUp: FileUp, download: Download, star: Star, sun: Sun, moon: Moon,
  x: X, check: Check, checkCircle: CheckCircle2, chevronDown: ChevronDown,
  chevronsRight: ChevronsRight, loader: Loader2, trash: Trash2, help: HelpCircle,
  settings: Settings, smartphone: Smartphone, bookOpen: BookOpen, book: Book,
  sparkles: Sparkles, plus: Plus, clock: Clock, fileText: FileText, archive: Archive,
  image: ImageIcon, heart: Heart, github: Github, mail: Mail, copy: Copy, send: Send,
  edit: Edit, crop: Crop, square: Square, user: User, chevronLeft: ChevronLeft,
  chevronRight: ChevronRight, bug: Bug,
};

const Comp = computed(() => MAP[props.name] || FileText);
</script>

<template>
  <component :is="Comp" :class="$props.class || 'h-4 w-4'" />
</template>
