<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const props = defineProps(['usuario'])
const solicitudesPendientes = ref([])
const procesando = ref(false)

// Cargar las solicitudes donde YO soy el jefe
const cargarPendientes = async () => {
  try {
    // Usamos el nuevo filtro ?jefe=ID
    const res = await axios.get(`http://127.0.0.1:8000/api/solicitudes/?jefe=${props.usuario.id}`)
    solicitudesPendientes.value = res.data
  } catch (e) {
    console.error("Error cargando bandeja jefe:", e)
  }
}

// Función para Aprobar o Rechazar el AVISO
const resolverAviso = async (solicitudId, decision) => {
  if (!confirm("¿Está seguro de esta acción?")) return

  procesando.value = true
  try {
    // decision debe ser 'AVISO_CONFIRMADO' o 'AVISO_NEGADO'
    await axios.patch(`http://127.0.0.1:8000/api/solicitudes/${solicitudId}/`, {
      estado: decision
    })
    
    alert("¡Respuesta guardada!")
    // Recargamos la lista para que desaparezca la que acabamos de tocar
    await cargarPendientes()
    
  } catch (e) {
    alert("Error al guardar decisión")
  } finally {
    procesando.value = false
  }
}

onMounted(() => {
  cargarPendientes()
})
</script>

<template>
  <div class="card border-primary mb-4 shadow-sm">
    <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
      <div class="d-flex align-items-center">
        <span class="fs-4 me-2">👮</span>
        <h5 class="mb-0">Modo Supervisor</h5>
      </div>
      <span class="badge bg-white text-primary rounded-pill fs-6">
        {{ solicitudesPendientes.length }} Pendientes
      </span>
    </div>

    <div class="card-body bg-light">
      <div v-if="solicitudesPendientes.length > 0" class="row row-cols-1 row-cols-md-2 g-3">
        <div v-for="soli in solicitudesPendientes" :key="soli.id" class="col">
          <div class="card h-100 border-0 shadow-sm">
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-start mb-2">
                <h6 class="card-title fw-bold text-primary mb-0">
                  {{ soli.apellido_agente }}, {{ soli.nombre_agente }}
                </h6>
                <span class="badge bg-warning text-dark">Pendiente</span>
              </div>
              
              <p class="card-text mb-1">
                <strong>📅 Fecha:</strong> {{ soli.fecha_inicio }} ({{ soli.dias }} días)
              </p>
              <p class="card-text mb-1 text-muted small">
                <strong>Tipo:</strong> {{ soli.tipo_descripcion || soli.tipo }}
              </p>
              <p class="card-text fst-italic bg-light p-2 rounded small border">
                "{{ soli.motivo || 'Sin comentarios' }}"
              </p>

              <a v-if="soli.archivo_adjunto" :href="soli.archivo_adjunto" target="_blank" class="btn btn-sm btn-outline-info mb-3 w-100">
                📎 Ver Certificado Adjunto
              </a>
            </div>

            <div class="card-footer bg-white border-top-0 d-flex gap-2">
              <button 
                class="btn btn-outline-danger flex-grow-1" 
                @click="resolverAviso(soli.id, 'AVISO_NEGADO')"
                :disabled="procesando"
              >
                No Avisó
              </button>
              <button 
                class="btn btn-success flex-grow-1 fw-bold" 
                @click="resolverAviso(soli.id, 'AVISO_CONFIRMADO')"
                :disabled="procesando"
              >
                ✅ Confirmar
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <div v-else class="text-center p-4 text-muted">
        <p class="mb-0">✅ ¡Al día! No tienes avisos pendientes de revisión.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>