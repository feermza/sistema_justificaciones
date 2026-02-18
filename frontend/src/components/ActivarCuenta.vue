<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'

const emit = defineEmits(['volver-login'])

// --- ESTADOS DEL WIZARD ---
const paso = ref(1) // 1: Identidad, 2: Definir Clave
const cargando = ref(false)
const error = ref('')
const mensajeExito = ref('')

// --- DATOS PASO 1 (Identidad) ---
const legajo = ref('')
const dni = ref('')

// Selectores de Fecha (Dropdowns)
const dia = ref('')
const mes = ref('')
const anio = ref('')

// Listas para los dropdowns
const dias = Array.from({length: 31}, (_, i) => i + 1)
const meses = [
  {id: 1, nom: 'Enero'}, {id: 2, nom: 'Febrero'}, {id: 3, nom: 'Marzo'},
  {id: 4, nom: 'Abril'}, {id: 5, nom: 'Mayo'}, {id: 6, nom: 'Junio'},
  {id: 7, nom: 'Julio'}, {id: 8, nom: 'Agosto'}, {id: 9, nom: 'Septiembre'},
  {id: 10, nom: 'Octubre'}, {id: 11, nom: 'Noviembre'}, {id: 12, nom: 'Diciembre'}
]
// Años desde 1950 hasta 2007 (aprox 18 años atrás)
const anios = Array.from({length: 58}, (_, i) => 2007 - i)

// --- DATOS PASO 2 (Seguridad) ---
const token = ref('') // El "pase" temporal que nos da el backend
const tipoUsuario = ref('') // 'pin' o 'password'
const password = ref('')
const passwordConfirm = ref('')
const mostrarPassword = ref(false) // Ojo para ver clave

// --- LÓGICA PASO 1: VALIDAR IDENTIDAD ---
const validarIdentidad = async () => {
  error.value = ''
  
  if (!legajo.value || !dni.value || !dia.value || !mes.value || !anio.value) {
    error.value = "Por favor complete todos los campos."
    return
  }

  cargando.value = true
  
  // Formateamos fecha para Django: YYYY-MM-DD
  // Aseguramos que día y mes tengan 2 dígitos (ej: 05)
  const fechaFmt = `${anio.value}-${String(mes.value).padStart(2, '0')}-${String(dia.value).padStart(2, '0')}`

  try {
    const payload = {
      legajo: legajo.value,
      dni: dni.value,
      fecha_nacimiento: fechaFmt
    }
    
    // Llamada al Backend
    const res = await axios.post('http://127.0.0.1:8000/api/agentes/validar_identidad/', payload)
    
    // Si sale bien:
    token.value = res.data.token       // Guardamos el pase
    tipoUsuario.value = res.data.tipo_usuario // 'pin' o 'password'
    paso.value = 2                     // Avanzamos de pantalla
    
  } catch (e) {
    console.error(e)
    if (e.response && e.response.data) {
      // Intentamos mostrar el mensaje específico del error (ej: "DNI incorrecto")
      // A veces viene como array o string directo
      const msg = Object.values(e.response.data).flat().join(', ')
      error.value = msg || "Error al validar identidad."
    } else {
      error.value = "Error de conexión con el servidor."
    }
  } finally {
    cargando.value = false
  }
}

// --- LÓGICA PASO 2: ACTIVAR CUENTA ---
const activarCuenta = async () => {
  error.value = ''

  // Validaciones Frontend básicas
  if (password.value !== passwordConfirm.value) {
    error.value = "Las contraseñas no coinciden."
    return
  }
  
  if (tipoUsuario.value === 'pin') {
    if (password.value.length !== 6 || isNaN(password.value)) {
      error.value = "El PIN debe ser de 6 números exactos."
      return
    }
  } else {
    if (password.value.length < 8) {
      error.value = "La contraseña debe tener al menos 8 caracteres."
      return
    }
  }

  cargando.value = true

  try {
    const payload = {
      token: token.value,
      password: password.value
    }
    
    await axios.post('http://127.0.0.1:8000/api/agentes/activar_cuenta/', payload)
    
    // ÉXITO TOTAL
    mensajeExito.value = "¡Cuenta activada con éxito! Ahora puedes ingresar."
    
    // Esperamos 2 segundos y volvemos al login automáticamente
    setTimeout(() => {
      emit('volver-login')
    }, 2500)

  } catch (e) {
    console.error(e)
    // 1. LIMPIEZA AUTOMÁTICA
    if (tipoUsuario.value === 'pin') {
        password.value = ''
        passwordConfirm.value = ''
    }

    if (e.response && e.response.data) {
      const msg = Object.values(e.response.data).flat().join(', ')
      error.value = msg || "Error al activar cuenta."
    } else {
      error.value = "Error de conexión."
    }
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <div class="card shadow-lg border-0 rounded-3" style="max-width: 450px; width: 100%;">
    
    <div class="card-header bg-success text-white text-center py-3">
      <h4 class="mb-0 fw-bold">🚀 Activar Cuenta</h4>
    </div>
    
    <div class="card-body p-4">
      
      <div v-if="mensajeExito" class="alert alert-success text-center">
        {{ mensajeExito }}
      </div>

      <div v-else>

        <div v-if="paso === 1">
          <p class="text-muted small text-center mb-4">
            Ingresa tus datos personales para verificar tu identidad.
          </p>

          <div class="mb-3">
            <label class="form-label fw-bold">Nro. Legajo</label>
            <input v-model="legajo" type="number" class="form-control" placeholder="Ej: 1234">
          </div>

          <div class="mb-3">
            <label class="form-label fw-bold">DNI</label>
            <input v-model="dni" type="text" class="form-control" placeholder="Ej: 30123456">
          </div>

          <div class="mb-4">
            <label class="form-label fw-bold">Fecha de Nacimiento</label>
            <div class="d-flex gap-2">
              <select v-model="dia" class="form-select">
                <option value="" disabled>Día</option>
                <option v-for="d in dias" :key="d" :value="d">{{ d }}</option>
              </select>
              <select v-model="mes" class="form-select">
                <option value="" disabled>Mes</option>
                <option v-for="m in meses" :key="m.id" :value="m.id">{{ m.nom }}</option>
              </select>
              <select v-model="anio" class="form-select">
                <option value="" disabled>Año</option>
                <option v-for="a in anios" :key="a" :value="a">{{ a }}</option>
              </select>
            </div>
          </div>

          <button @click="validarIdentidad" :disabled="cargando" class="btn btn-success w-100 fw-bold">
            {{ cargando ? 'Verificando...' : 'Continuar' }}
          </button>
        </div>

        <div v-else>
          <div class="text-center mb-4">
            <h5 class="fw-bold text-primary">Hola, {{ legajo }}</h5>
            <p class="text-muted small">
              {{ tipoUsuario === 'pin' ? 'Crea tu PIN numérico de acceso.' : 'Define tu contraseña segura.' }}
            </p>
          </div>

          <div class="mb-3">
            <label class="form-label fw-bold">
              {{ tipoUsuario === 'pin' ? 'Tu Nuevo PIN (6 dígitos)' : 'Nueva Contraseña' }}
            </label>
            

            <div class="input-group">
              <input 
                :type="mostrarPassword ? 'text' : 'password'"
                v-model="password" 
                class="form-control text-center fw-bold fs-4" 
                :maxlength="tipoUsuario === 'pin' ? 6 : 20"
                :inputmode="tipoUsuario === 'pin' ? 'numeric' : 'text'"
                placeholder="******"
              >
            </div>
            
            <small class="text-muted" v-if="tipoUsuario === 'pin'">
              Solo números. No uses fechas ni DNI.
            </small>
            <small class="text-muted" v-else>
              Mínimo 8 caracteres, letras y números.
            </small>
          </div>

          <div class="mb-4">
            <label class="form-label fw-bold">Repetir para confirmar</label>
            <input 
              :type="mostrarPassword ? 'text' : 'password'"
              v-model="passwordConfirm" 
              class="form-control text-center fw-bold fs-4" 
              :maxlength="tipoUsuario === 'pin' ? 6 : 20"
              :inputmode="tipoUsuario === 'pin' ? 'numeric' : 'text'"
              placeholder="******"
            >
          </div>

          <button @click="activarCuenta" :disabled="cargando" class="btn btn-primary w-100 fw-bold">
            {{ cargando ? 'Activando...' : 'Finalizar Activación' }}
          </button>
        </div>

        <div v-if="error" class="alert alert-danger mt-3 text-center small">
          {{ error }}
        </div>

      </div>
    </div>

    <div class="card-footer text-center py-3 bg-light">
      <a href="#" class="text-decoration-none text-muted" @click.prevent="$emit('volver-login')">
        ← Volver al Login
      </a>
    </div>
  </div>
</template>
