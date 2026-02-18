<script setup>
// Props: Datos que recibimos del padre (App.vue)
defineProps({
  usuario: {
    type: Object,
    required: true
  }
})

// Emits: Eventos que enviamos al padre
const emit = defineEmits(['cerrar-sesion'])
</script>

<template>
  <nav class="navbar navbar-expand-lg navbar-dark bg-primary shadow-sm">
    <div class="container">
      
      <a class="navbar-brand fw-bold d-flex align-items-center gap-2" href="#">
        <span style="font-size: 1.5rem;">🎓</span>
        <span>UTN Justificaciones</span>
      </a>

      <div class="d-flex text-white align-items-center gap-3">
        <div class="d-none d-md-block text-end line-height-sm">
          <div class="small text-white-50">Bienvenido/a</div>
          <div class="fw-bold">
            {{ usuario.nombre }} {{ usuario.apellido }}
          </div>
        </div>

        <button 
          class="btn btn-outline-light btn-sm d-flex align-items-center gap-2" 
          @click="emit('cerrar-sesion')"
          title="Cerrar Sesión"
        >
          <span class="d-none d-sm-inline">Salir</span>
          <span>🚪</span>
        </button>
      </div>

    </div>
  </nav>
</template>

<style scoped>
.line-height-sm {
  line-height: 1.2;
}
</style>