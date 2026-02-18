<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const props = defineProps(['usuario'])
const emit = defineEmits(['editar'])
const misSolicitudes = ref([])
const cargando = ref(true)

const cargarMisSolicitudes = async () => {
  cargando.value = true
  try {
    // Filtramos por MI id de agente
    const res = await axios.get(`http://127.0.0.1:8000/api/solicitudes/?agente=${props.usuario.id}`)
    misSolicitudes.value = res.data
  } catch (e) {
    console.error("Error cargando historial:", e)
  } finally {
    cargando.value = false
  }
}

// Función para cancelar (borrar) una solicitud si todavía está pendiente
const cancelarSolicitud = async (id) => {
  if (!confirm("¿Seguro que deseas cancelar y eliminar esta solicitud?")) return

  try {
    await axios.delete(`http://127.0.0.1:8000/api/solicitudes/${id}/`)
    alert("Solicitud cancelada.")
    cargarMisSolicitudes()
  } catch (e) {
    alert("No se pudo eliminar. Quizás ya fue procesada por tu jefe.")
  }
}

onMounted(() => {
  cargarMisSolicitudes()
})

// Exponemos la función de recarga para que el padre pueda llamarla
defineExpose({ cargarMisSolicitudes })
</script>

<template>
  <div class="card shadow-sm border-0">
    <div class="card-header bg-white py-3">
      <h5 class="mb-0 fw-bold text-secondary">📄 Mi Historial de Solicitudes</h5>
    </div>
    
    <div class="card-body">
      <div v-if="cargando" class="text-center py-3">
        <div class="spinner-border text-primary" role="status"></div>
      </div>

      <div v-else-if="misSolicitudes.length > 0" class="table-responsive">
        <table class="table table-hover align-middle">
          <thead class="table-light">
            <tr>
              <th>Fecha</th>
              <th>Licencia</th>
              <th>Días</th>
              <th>Estado</th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="soli in misSolicitudes" :key="soli.id">
              <td>{{ soli.fecha_inicio }}</td>
              <td>{{ soli.tipo_descripcion }}</td>
              <td><span class="badge bg-light text-dark border">{{ soli.dias }}</span></td>
              
              <td>
                <span v-if="soli.estado === 'PENDIENTE_VALIDACION'" class="badge bg-warning text-dark">En Revisión</span>
                <span v-else-if="soli.estado === 'AVISO_CONFIRMADO'" class="badge bg-info text-dark">Jefe OK</span>
                <span v-else-if="soli.estado === 'IMPACTADO'" class="badge bg-success">Aprobada</span>
                <span v-else-if="soli.estado === 'AVISO_NEGADO'" class="badge bg-danger">Aviso Negado</span>
                <span v-else class="badge bg-secondary">{{ soli.estado }}</span>
              </td>

              <td class="text-end">
                
                <div v-if="soli.estado === 'PENDIENTE_VALIDACION'">
                  <button 
                    class="btn btn-sm btn-outline-primary me-2" 
                    @click="$emit('editar', soli)" 
                    title="Editar Solicitud"
                  >
                    ✏️
                  </button>
                  <button 
                    class="btn btn-sm btn-outline-danger" 
                    @click="cancelarSolicitud(soli.id)" 
                    title="Cancelar Solicitud"
                  >
                    🗑️
                  </button>
                </div>

                <div v-else class="text-muted" title="Solicitud cerrada/procesada">
                  🔒 <small>Cerrado</small>
                </div>

              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else class="text-center py-4 text-muted bg-light rounded">
        No tienes solicitudes cargadas recientemente.
      </div>
    </div>
  </div>
</template>