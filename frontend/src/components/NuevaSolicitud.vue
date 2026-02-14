<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import axios from 'axios'

// Recibimos 'solicitudEdicion'. Si es null, es una carga nueva.
const props = defineProps({
  usuario: Object,
  solicitudEdicion: Object 
})

const emit = defineEmits(['volver', 'guardado-ok'])

const tiposLicencia = ref([])
const supervisores = ref([])
const enviando = ref(false)

// Estado del formulario
const form = reactive({
  tipo: '',
  fecha_inicio: '',
  dias: 1,
  motivo: '',
  jefe: '',
  archivo: null
})

// Computada: ¿Estamos editando?
const esEdicion = computed(() => !!props.solicitudEdicion)

// Al iniciar, cargamos listas y rellenamos datos si es edición
onMounted(async () => {
  await cargarMaestros()
  
  if (esEdicion.value) {
    const s = props.solicitudEdicion
    // Rellenamos el formulario con los datos existentes
    form.tipo = s.tipo 
    form.fecha_inicio = s.fecha_inicio
    form.dias = s.dias
    form.motivo = s.motivo
    form.jefe = s.jefe_seleccionado
    // Nota: El archivo no se puede precargar por seguridad del navegador
  }
})

const cargarMaestros = async () => {
  try {
    const resTipos = await axios.get('http://127.0.0.1:8000/api/licencias/')
    tiposLicencia.value = resTipos.data
    
    // Traemos al agente completo para ver sus supervisores
    const resAgente = await axios.get(`http://127.0.0.1:8000/api/agentes/${props.usuario.id}/`)
    supervisores.value = resAgente.data.supervisores_detalle || [] 
  } catch (e) {
    console.error("Error cargando datos:", e)
  }
}

const manejarArchivo = (event) => {
  form.archivo = event.target.files[0]
}

const guardar = async () => {
  if (!form.tipo || !form.fecha_inicio || !form.jefe) {
    alert("Por favor complete los campos obligatorios.")
    return
  }

  enviando.value = true
  
  // Usamos FormData para poder enviar archivos
  const datos = new FormData()
  datos.append('agente', props.usuario.id)
  datos.append('tipo', form.tipo)
  datos.append('fecha_inicio', form.fecha_inicio)
  datos.append('dias', form.dias)
  datos.append('jefe_seleccionado', form.jefe)
  datos.append('motivo', form.motivo)
  
  if (form.archivo) {
    datos.append('archivo_adjunto', form.archivo)
  }

  try {
    if (esEdicion.value) {
      // MODO EDICIÓN: PATCH (Actualizar)
      await axios.patch(`http://127.0.0.1:8000/api/solicitudes/${props.solicitudEdicion.id}/`, datos)
      alert("✅ Solicitud actualizada correctamente.")
    } else {
      // MODO CREACIÓN: POST (Crear nueva)
      await axios.post('http://127.0.0.1:8000/api/solicitudes/', datos)
      alert("✅ Solicitud enviada correctamente.")
    }
    
    emit('guardado-ok')
    
  } catch (e) {
    console.error(e)
    if (e.response && e.response.data) {
       // Mostramos errores del backend (ej: Topes o Duplicados)
       alert("Error: " + JSON.stringify(e.response.data))
    } else {
       alert("Error al guardar.")
    }
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <div class="card shadow">
    <div class="card-header bg-success text-white">
      <h4 class="mb-0">{{ esEdicion ? '✏️ Editar Solicitud' : '➕ Nueva Solicitud' }}</h4>
    </div>
    <div class="card-body">
      <form @submit.prevent="guardar">
        
        <!-- FILA 1: Tipo de Licencia (ancho completo) -->
        <div class="row">
          <div class="col-12 mb-3">
            <label class="form-label fw-semibold">Tipo de Licencia <span class="text-danger">*</span></label>
            <select v-model="form.tipo" class="form-select" required>
              <option disabled value="">Seleccione...</option>
              <option v-for="t in tiposLicencia" :key="t.id" :value="t.id">
                {{ t.descripcion }}
              </option>
            </select>
          </div>
        </div>

        <!-- FILA 2: Fecha Inicio, Días y Supervisor -->
        <div class="row">
          <div class="col-md-4 mb-3">
            <label class="form-label fw-semibold">Fecha Inicio <span class="text-danger">*</span></label>
            <input v-model="form.fecha_inicio" type="date" class="form-control" required>
          </div>
          
          <div class="col-md-2 mb-3">
            <label class="form-label fw-semibold">Días <span class="text-danger">*</span></label>
            <input v-model="form.dias" type="number" min="1" class="form-control" required>
          </div>

          <div class="col-md-6 mb-3">
            <label class="form-label fw-semibold">¿A quién le avisas? <span class="text-danger">*</span></label>
            <select v-model="form.jefe" class="form-select" required>
              <option disabled value="">Seleccionar Supervisor...</option>
              <option v-for="sup in supervisores" :key="sup.id" :value="sup.id">
                {{ sup.apellido }}, {{ sup.nombre }}
              </option>
            </select>
          </div>
        </div>

        <!-- FILA 3: Motivo -->
        <div class="row">
          <div class="col-12 mb-3">
            <label class="form-label fw-semibold">Motivo <small class="text-muted">(Opcional)</small></label>
            <textarea v-model="form.motivo" class="form-control" rows="3" 
                      placeholder="Describe brevemente el motivo de tu solicitud..."></textarea>
          </div>
        </div>

        <!-- FILA 4: Adjuntar Certificado -->
        <div class="row">
          <div class="col-12 mb-4">
            <label class="form-label fw-semibold">Adjuntar Certificado <small class="text-muted">(Opcional)</small></label>
            <input type="file" @change="manejarArchivo" class="form-control" accept=".jpg,.png,.pdf">
            <small v-if="esEdicion" class="text-muted d-block mt-1">
              <i class="bi bi-info-circle"></i> Si no sube nada, se mantiene el archivo anterior.
            </small>
            <small v-else class="text-muted d-block mt-1">
              Formatos permitidos: JPG, PNG, PDF (máx. 5MB)
            </small>
          </div>
        </div>

        <!-- Botones de acción -->
        <div class="d-flex justify-content-between align-items-center pt-3 border-top">
          <button type="button" class="btn btn-outline-secondary px-4" @click="$emit('volver')">
            <i class="bi bi-arrow-left"></i> Cancelar
          </button>
          <button type="submit" class="btn btn-success px-4" :disabled="enviando">
            <span v-if="enviando">
              <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
              Guardando...
            </span>
            <span v-else>
              <i :class="esEdicion ? 'bi bi-check-circle' : 'bi bi-send'"></i>
              {{ esEdicion ? 'Guardar Cambios' : 'Enviar Solicitud' }}
            </span>
          </button>
        </div>

      </form>
    </div>
  </div>
</template>

<style scoped>
/* Mejoras visuales adicionales */
.form-label {
  margin-bottom: 0.5rem;
  color: #495057;
}

.form-control:focus,
.form-select:focus {
  border-color: #28a745;
  box-shadow: 0 0 0 0.2rem rgba(40, 167, 69, 0.25);
}

.card {
  border-radius: 0.5rem;
  border: none;
}

.card-header {
  border-radius: 0.5rem 0.5rem 0 0 !important;
  padding: 1.25rem 1.5rem;
}

.card-body {
  padding: 2rem 1.5rem;
}

/* Responsive: en pantallas pequeñas, todo al 100% */
@media (max-width: 768px) {
  .col-md-4, .col-md-2, .col-md-6 {
    width: 100%;
  }
}
</style>
