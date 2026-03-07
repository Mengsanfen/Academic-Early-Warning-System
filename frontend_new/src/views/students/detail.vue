<template>
  <div class="page-container">
    学生详情页 - {{ id }}
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
const id = route.params.id
</script>
