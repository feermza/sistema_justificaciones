<script setup>
import { ref } from 'vue'
import axios from 'axios'

const emit = defineEmits(['login-exitoso', 'ir-a-activar'])

const legajo = ref('')
const password = ref('') // Antes era DNI, ahora es Password/PIN
const error = ref('')
const cargando = ref(false)
const mostrarPassword = ref(false)

const intentarIngresar = async () => {
  error.value = ''
  
  if (!legajo.value || !password.value) {
    error.value = "Por favor complete Legajo y Contraseña."
    return
  }

  cargando.value = true
  
  try {
    // CAMBIO CRÍTICO: Ahora usamos POST al endpoint de login real
    const payload = {
      legajo: legajo.value,
      password: password.value
    }

    const respuesta = await axios.post('http://127.0.0.1:8000/api/agentes/login/', payload)
    
    // Si llegamos acá, es 200 OK
    const agenteEncontrado = respuesta.data
    emit('login-exitoso', agenteEncontrado)

  } catch (e) {
    console.error(e)
    if (e.response && e.response.status === 401) {
      error.value = 'Legajo o Contraseña incorrectos.'
    } else if (e.response && e.response.data.error) {
      error.value = e.response.data.error
    } else {
      error.value = 'Error de conexión con el servidor.'
    }
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
          @keyup.enter="intentarIngresar"
        >
      </div>

      <div class="mb-4">
        <label class="form-label fw-bold">Contraseña / PIN</label>
        <div class="input-group">
          <input 
            :type="mostrarPassword ? 'text' : 'password'"
            v-model="password" 
            class="form-control form-control-lg" 
            placeholder="Ingrese su clave..."
            @keyup.enter="intentarIngresar"
          >
          <button class="btn btn-outline-secondary" type="button" @click="mostrarPassword = !mostrarPassword">
            👁️
          </button>
        </div>
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
      <p class="mb-1 text-muted small">¿Es tu primera vez?</p>
      <a href="#" class="fw-bold text-success text-decoration-none" @click.prevent="$emit('ir-a-activar')">
        🚀 Activar mi cuenta
      </a>
    </div>
  </div>
</template>