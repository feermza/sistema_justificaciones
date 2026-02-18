<script setup>
import { ref } from 'vue'

// --- COMPONENTES ESTRUCTURALES ---
import AppHeader from './components/AppHeader.vue'
import AppFooter from './components/AppFooter.vue'

// --- VISTAS DEL SISTEMA ---
import Login from './components/Login.vue'
import ActivarCuenta from './components/ActivarCuenta.vue'
import NuevaSolicitud from './components/NuevaSolicitud.vue'
import BandejaJefe from './components/BandejaJefe.vue'
import BandejaRRHH from './components/BandejaRRHH.vue'
import MisSolicitudes from './components/MisSolicitudes.vue'

// --- ESTADO GLOBAL ---
const usuarioActual = ref(null)
const mostrarActivacion = ref(false)
const mostrarFormulario = ref(false)
const refHistorial = ref (null)
const solicitudParaEditar = ref(null)

// --- LÓGICA DE NAVEGACIÓN ---
const alLoguearse = (agente) => { usuarioActual.value = agente }
const cerrarSesion = () => {
  usuarioActual.value = null
  mostrarFormulario.value = false
}
const irAActivacion = () => { mostrarActivacion.value = true }
const irALogin = () => { mostrarActivacion.value = false }

// --- LÓGICA DE EDICIÓN / CREACIÓN ---

// 1. Abrir formulario para carga NUEVA (Limpia datos anteriores)
const abrirNuevaSolicitud = () => {
  solicitudParaEditar.value = null 
  mostrarFormulario.value = true
}

// 2. Abrir formulario para EDITAR (Carga datos existentes)
const iniciarEdicion = (solicitud) => {
  solicitudParaEditar.value = solicitud
  mostrarFormulario.value = true
}

// 3. Al terminar (Guardar o Cancelar)
const cerrarFormulario = () => {
  mostrarFormulario.value = false
  // Recargamos el historial por si hubo cambios
  setTimeout(() => {
    if (refHistorial.value) refHistorial.value.cargarMisSolicitudes()
  }, 500)
}
</script>

<template>
  <div class="d-flex flex-column min-vh-100 bg-light">
    
    <div v-if="!usuarioActual" class="flex-grow-1 d-flex justify-content-center align-items-center">
      <div v-if="mostrarActivacion" class="w-100 d-flex justify-content-center">
        <ActivarCuenta @volver-login="irALogin" />
      </div>
      <div v-else class="w-100 d-flex justify-content-center">
        <Login @login-exitoso="alLoguearse" @ir-a-activar="irAActivacion" />
      </div>
    </div>

    <div v-else class="d-flex flex-column flex-grow-1">
      <AppHeader :usuario="usuarioActual" @cerrar-sesion="cerrarSesion" />

      <main class="container py-4 flex-grow-1">
        
        <div v-if="mostrarFormulario">
          <NuevaSolicitud 
            :usuario="usuarioActual"
            :solicitudEdicion="solicitudParaEditar" 
            @volver="mostrarFormulario = false" 
            @guardado-ok="cerrarFormulario" 
          />
        </div>

        <div v-else>
          
          <div class="d-flex justify-content-between align-items-center mb-4">
            <h3 class="text-dark fw-bold mb-0">Panel de Control</h3>
            <button class="btn btn-success btn-lg shadow-sm fw-bold" @click="abrirNuevaSolicitud">
              <span class="me-2">➕</span> Nueva Solicitud
            </button>
          </div>

          <div v-if="usuarioActual.es_jefe || usuarioActual.es_rrhh" class="mb-5">
             <BandejaJefe :usuario="usuarioActual" />
          </div>

          <div v-if="usuarioActual.es_rrhh" class="mb-5">
            <BandejaRRHH :usuario="usuarioActual" />
          </div>

          <div class="mb-4">
            <MisSolicitudes 
              ref="refHistorial" 
              :usuario="usuarioActual" 
              @editar="iniciarEdicion"
            />
          </div>

        </div>

      </main>

      <AppFooter />
    </div>
  </div>
</template>

<style>
/* Estilos Globales (opcional) */
body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
</style>