<script setup>
import { ref } from 'vue'
import axios from 'axios'
import Login from './components/Login.vue'
import NuevaSolicitud from './components/NuevaSolicitud.vue' // <--- IMPORTAR
import BandejaJefe from './components/BandejaJefe.vue'
import BandejaRRHH from './components/BandejaRRHH.vue'
import ActivarCuenta from './components/ActivarCuenta.vue'

// Estado: ¿Tenemos un usuario logueado? Al principio es null (nadie)
const usuarioActual = ref(null)
const misSolicitudes = ref([])
const cargandoDatos = ref(false)
const mostrarFormulario = ref(false)
const solicitudAEditar = ref(null)
const mostrarActivacion = ref(false)

// Función que se ejecuta cuando el Login avisa que tuvo éxito
const alLoguearse = async (agente) => {
  usuarioActual.value = agente
  await cargarSolicitudes(agente.id)
}

//Función para pedir datos a Django
const cargarSolicitudes = async (agenteId) => {
  cargandoDatos.value = true
  try {
    const res = await axios.get(`http://127.0.0.1:8000/api/solicitudes/?agente=${agenteId}`)
  misSolicitudes.value = res.data  
  } catch (e) {
    console.error("Error cargando historial:", e)
    alert("No se pudo cargar el historial")
  } finally {
    cargandoDatos.value = false
  }
}

// FUNCIÓN: ELIMINAR SOLICITUD
const eliminarSolicitud = async (id) => {
  if (!confirm("¿Seguro que deseas ANULAR esta solicitud? Se avisará a tu jefe que ha sido cancelada.")) return;

  try {
    await axios.delete(`http://127.0.0.1:8000/api/solicitudes/${id}/`)
    alert("Solicitud eliminada y aviso de cancelación enviado.")
    // Recargamos la lista
    await cargarSolicitudes(usuarioActual.value.id)
  } catch (error) {
    console.error(error)
    alert("No se pudo eliminar. Verifique que la solicitud siga pendiente.")
  }
}

// FUNCIÓN PARA EDITAR (Lápiz)
const abrirEdicion = (solicitud) => {
  solicitudAEditar.value = solicitud // Guardamos los datos de la fila seleccionada
  mostrarFormulario.value = true     // Mostramos el componente
}

// FUNCIÓN PARA CREAR (Botón Verde)
const abrirNueva = () => {
  solicitudAEditar.value = null      // Limpiamos para que esté vacío
  mostrarFormulario.value = true
}

// Funciones para navegar
const irAActivacion = () => { mostrarActivacion.value = true }
const irALogin = () => { mostrarActivacion.value = false }

const cerrarSesion = () => {
  usuarioActual.value = null
  misSolicitudes.value = []
}

//Función auxiliar para dar color al estado
// Función para devolver la clase de Bootstrap según el estado
const claseBadge = (estado) => {
  if (estado === 'IMPACTADO' || estado === 'APROBADO') return 'text-bg-success' // Verde
  if (estado === 'AVISO_CONFIRMADO') return 'text-bg-primary' // Azul
  if (estado && (estado.includes('RECHAZADO') || estado.includes('NEGADO'))) return 'text-bg-danger' // Rojo
  return 'text-bg-warning text-dark' // Amarillo (Pendiente)
}
</script>

<template>
  <div class="min-vh-100 bg-light">
    
    <div v-if="!usuarioActual" class="d-flex justify-content-center align-items-center min-vh-100">
      <div v-if="mostrarActivacion">
        <ActivarCuenta @volver-login="irALogin" />
      </div>

      <div v-else>
        <Login @login-exitoso="alLoguearse" @ir-a-activar="irAActivacion" />
      </div>
    </div>

    <div v-else>
      <nav class="navbar navbar-expand-lg navbar-dark bg-primary shadow">
        <div class="container">
          <a class="navbar-brand fw-bold" href="#">🎓 UTN Justificaciones</a>
          <div class="d-flex align-items-center text-white">
            <span class="me-3 d-none d-md-block">
              Hola, <strong>{{ usuarioActual.nombre }} {{ usuarioActual.apellido }}</strong>
            </span>
            <button @click="cerrarSesion" class="btn btn-outline-light btn-sm">
              Cerrar Sesión
            </button>
          </div>
        </div>
      </nav>

      <div class="container my-5">
        
        <div v-if="mostrarFormulario">
          <NuevaSolicitud 
            :usuario="usuarioActual"
            :solicitud-edicion="solicitudAEditar"
            @volver="mostrarFormulario = false"
            @guardado-ok="() => { mostrarFormulario = false; cargarSolicitudes(usuarioActual.id); }" 
          />
        </div>

        <div v-else>
          
          <div class="mb-4">
            <BandejaJefe v-if="usuarioActual.es_jefe" :usuario="usuarioActual" />
            <BandejaRRHH v-if="usuarioActual.es_rrhh" :usuario="usuarioActual" />
          </div>

          <div class="card shadow-sm">
            <div class="card-header bg-white d-flex justify-content-between align-items-center py-3">
              <h5 class="mb-0 text-primary fw-bold">📄 Mis Solicitudes</h5>
              <button class="btn btn-success" @click="abrirNueva">
                + Nueva Solicitud
              </button>
            </div>
            
            <div class="card-body p-0">
              <div v-if="cargandoDatos" class="text-center p-5">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-2 text-muted">Cargando historial...</p>
              </div>

              <div v-else-if="misSolicitudes.length === 0" class="text-center p-5 text-muted">
                <p>No tienes solicitudes registradas en el historial.</p>
              </div>

              <div v-else class="table-responsive">
                <table class="table table-hover table-striped mb-0 align-middle">
                  <thead class="table-light">
                    <tr>
                      <th>Fecha</th>
                      <th>Tipo de Licencia</th>
                      <th>Días</th>
                      <th>Estado</th>
                      <th class="text-end">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="soli in misSolicitudes" :key="soli.id">
                      <td class="fw-bold">{{ soli.fecha_inicio }}</td>
                      <td>{{ soli.tipo_descripcion || soli.tipo }}</td> 
                      <td>{{ soli.dias }}</td>
                      <td>
                        <span class="badge rounded-pill" :class="claseBadge(soli.estado)">
                          {{ soli.estado }}
                        </span>
                      </td>

                      <td class="text-end pe-3">
                        <div v-if="soli.estado === 'PENDIENTE_VALIDACION'">
                          <button class="btn btn-sm btn-outline-primary me-2" @click="abrirEdicion(soli)" title="Editar">
                             ✏️
                          </button>
                          <button class="btn btn-sm btn-outline-danger"
                            @click="eliminarSolicitud(soli.id)"
                            title="Anular Solicitud">
                            🗑️
                          </button>
                        </div>

                        <span v-else class="text-muted small">🔒</span>
                      </td>
                      
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  </div>
</template>

<style>
/* Solo estilos personalizados mínimos, Bootstrap hace el resto */
body { background-color: #f8f9fa; }
</style>