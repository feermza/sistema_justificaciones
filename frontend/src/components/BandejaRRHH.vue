<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const props = defineProps(['usuario'])
const listaRRHH = ref([])
const procesando = ref(false)
const fechaDesde = ref('')
const fechaHasta = ref('')

const cargarParaRRHH = async () => {
  try {
    // Pedimos al backend con el "flag" de RRHH
    const res = await axios.get(`http://127.0.0.1:8000/api/solicitudes/?modo_rrhh=true`)
    listaRRHH.value = res.data
  } catch (e) {
    console.error("Error RRHH:", e)
  }
}

const dictaminar = async (solicitudId, decision) => {
let motivo = null;

// Paso 1: Interfaz de usuario (Decidir qué preguntar)
// Caso A: Si es un RECHAZO pedimos motivo obligatorio
if (decision === 'RECHAZADO') {
  // El 'prompt' detiene la ejecución hasta que el usuario escribe y acepta
  motivo = prompt("⚠️ Escriba el motivo del rechazo (Obligatorio): ");

  // Si el usuario da "Cancelar" (null) o lo deja en blanco ("")
  if (motivo === null || motivo.trim() === "") {
    return; // Cancelamos todo!! no se envía nada al servidor
  }
}

// Caso B: Si es Aprobación, solol confirmamos si/no
else {
  if (!confirm("¿Está seguro de APROBAR esta solicitud?")) return
}

// Paso 2: Envío al servidor
  procesando.value = true
  try {
    await axios.patch(`http://127.0.0.1:8000/api/solicitudes/${solicitudId}/`, {
      estado: decision
    })

    alert(decision === 'IMPACTADO' ? "✅ Solicitud Aprobada." : "⛔ Solicitud Rechazada con motivo.");
    await cargarParaRRHH()

  } catch (e) {
    alert("❌ Error al guardar en el sistema.")
  } finally {
    procesando.value = false
  }
}

const colorBorde = (estado) => {
    if (estado === 'AVISO_CONFIRMADO') return 'borde-azul'
    if (estado === 'IMPACTADO') return 'borde-verde'
    return 'borde-gris'
}

onMounted(() => {
  cargarParaRRHH()
})

// Función para descargar
const descargarReporte = () => {
  if (!fechaDesde.value || !fechaHasta.value) {
    alert("⚠️ Por favor seleccione fecha DESDE y HASTA para generar el reporte.")
    return
  }

  // Generamos la URL del Backend
  const url = `http://127.0.0.1:8000/api/solicitudes/exportar_excel/?desde=${fechaDesde.value}&hasta=${fechaHasta.value}`
  
  // Abrimos esa URL en una pestaña nueva (esto dispara la descarga automática)
  window.open(url, '_blank')
}

// Opcional: Cargar fechas por defecto (Ej: el mes actual) al iniciar
onMounted(() => {
    // ... tu código existente ...
    
    // Poner por defecto el primer y último día del mes actual
    const hoy = new Date();
    const primerDia = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
    const ultimoDia = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0);
    
    // Formato YYYY-MM-DD para el input HTML
    fechaDesde.value = primerDia.toISOString().split('T')[0]
    fechaHasta.value = ultimoDia.toISOString().split('T')[0]
})

</script>

<template>
  <div class="card border-dark mb-4 shadow-sm">
    <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
      <div class="d-flex align-items-center">
        <span class="fs-4 me-2">🏢</span>
        <h5 class="mb-0">Administración de Personal (RRHH)</h5>
      </div>
      <button class="btn btn-sm btn-outline-light" @click="cargarParaRRHH">
        🔄 Actualizar
      </button>
    </div>

    <div class="card-body bg-white border-bottom p-3">
      <div class="row g-2 align-items-end">
        <div class="col-auto">
          <span class="fw-bold text-muted small">EXPORTAR REPORTE:</span>
        </div>
        
        <div class="col-auto">
          <label class="small text-muted">Desde:</label>
          <input type="date" v-model="fechaDesde" class="form-control form-control-sm">
        </div>

        <div class="col-auto">
          <label class="small text-muted">Hasta:</label>
          <input type="date" v-model="fechaHasta" class="form-control form-control-sm">
        </div>

        <div class="col-auto">
          <button class="btn btn-sm btn-success" @click="descargarReporte">
            📥 Descargar Excel
          </button>
        </div>
      </div>
    </div>

    <div class="card-body bg-light">
      <div v-if="listaRRHH.length > 0" class="table-responsive">
        <table class="table table-hover align-middle bg-white rounded shadow-sm">
          <thead class="table-secondary">
            <tr>
              <th>Agente</th>
              <th>Licencia</th>
              <th>Fecha</th>
              <th>Estado</th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="soli in listaRRHH" :key="soli.id">
              <td>
                <div class="fw-bold">{{ soli.apellido_agente }}, {{ soli.nombre_agente }}</div>
                <small class="text-muted">Leg: {{ soli.agente }}</small>
              </td>
              <td>{{ soli.tipo_descripcion || soli.tipo }}</td>
              <td>{{ soli.fecha_inicio }} <span class="badge bg-secondary ms-1">{{ soli.dias }}d</span></td>
              <td>
                <span v-if="soli.estado === 'AVISO_CONFIRMADO'" class="badge text-bg-primary">
                  Jefe OK
                </span>
                
                <span v-else-if="soli.estado === 'AVISO_NEGADO'" class="badge bg-warning text-white border border-dark">
                  Jefe: No Avisó
                </span>

                <span v-else-if="soli.estado === 'IMPACTADO'" class="badge text-bg-success">Aprobado</span>
                <span v-else class="badge text-bg-danger">Rechazado</span>
              </td>
              
              <td class="text-end">
                 <div v-if="['AVISO_CONFIRMADO', 'AVISO_NEGADO'].includes(soli.estado)" class="btn-group btn-group-sm">
                  
                  <a v-if="soli.archivo_adjunto" :href="soli.archivo_adjunto" target="_blank" class="btn btn-outline-secondary" title="Ver Adjunto">
                    📎
                  </a>

                  <button class="btn btn-outline-danger" @click="dictaminar(soli.id, 'RECHAZADO')" :disabled="procesando">Rechazar</button>
                  
                  <button class="btn btn-success fw-bold" @click="dictaminar(soli.id, 'IMPACTADO')" :disabled="procesando">APROBAR</button>
                </div>
                
                <span v-else class="text-muted fst-italic small">
                  {{ soli.estado === 'IMPACTADO' ? 'Cerrado (Aprobado)' : 'Cerrado (Rechazado)' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <div v-else class="text-center p-4 text-muted">
        <p class="mb-0">No hay trámites en la bandeja de entrada.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>