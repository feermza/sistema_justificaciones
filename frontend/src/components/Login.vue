<script setup>
import { ref } from 'vue'
import axios from 'axios'

// Definimos los eventos que este componente puede enviar al padre (App.vue)
const emit = defineEmits(['login-exitoso'])

const legajo = ref('')
const dni = ref('')
const error = ref('')
const cargando = ref(false)

const intentarIngresar = async () => {
  error.value = ''
  cargando.value = true
  
  try {
    // Consultamos a tu API nueva con los filtros
    const respuesta = await axios.get(`http://127.0.0.1:8000/api/agentes/?legajo=${legajo.value}&dni=${dni.value}`)
    
    // Si la lista tiene al menos 1 resultado, es que los datos son correctos
    if (respuesta.data.length > 0) {
      const agenteEncontrado = respuesta.data[0]
      // Avisamos a App.vue que encontramos al usuario
      emit('login-exitoso', agenteEncontrado)
    } else {
      error.value = 'Legajo o DNI incorrectos. Verifique sus datos.'
    }
  } catch (e) {
    error.value = 'Error de conexión con el servidor.'
    console.error(e)
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <div class="card shadow-lg border-0 rounded-3" style="max-width: 400px; width: 100%;">
    <div class="card-header bg-primary text-white text-center py-3">
      <h4 class="mb-0 fw-bold">🔐 Acceso UTN</h4>
    </div>
    
    <div class="card-body p-4">
      <p class="text-muted text-center mb-4">Portal de Justificaciones</p>
      
      <div class="mb-3">
        <label class="form-label fw-bold">Nro. Legajo</label>
        <input 
          v-model="legajo" 
          type="number" 
          class="form-control form-control-lg" 
          placeholder="Ej: 1234"
        >
      </div>

      <div class="mb-4">
        <label class="form-label fw-bold">DNI (Sin puntos)</label>
        <input 
          v-model="dni" 
          type="text" 
          class="form-control form-control-lg" 
          placeholder="Ej: 30123456"
        >
      </div>

      <div v-if="error" class="alert alert-danger text-center" role="alert">
        {{ error }}
      </div>

      <button 
        @click="intentarIngresar" 
        :disabled="cargando"
        class="btn btn-primary w-100 btn-lg fw-bold"
      >
        <span v-if="cargando" class="spinner-border spinner-border-sm me-2"></span>
        {{ cargando ? 'Verificando...' : 'Ingresar al Sistema' }}
      </button>
    </div>
    <div class="card-footer text-center py-3 bg-light">
      <small class="text-muted">Departamento de Personal</small>
    </div>
  </div>
</template>

<style scoped>
/* Solo necesitamos esto si queremos ajustes finos */
</style>