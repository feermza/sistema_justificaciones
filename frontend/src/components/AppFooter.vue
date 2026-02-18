<script setup>
// No requiere lógica por ahora, es solo visual
const anioActual = new Date().getFullYear()
</script>

<template>
  <footer class="bg-dark text-light py-4 mt-auto border-top border-secondary">
    <div class="container">
      <div class="row align-items-center text-center text-md-start">
        
        <div class="col-md-4 mb-3 mb-md-0">
          <h6 class="text-uppercase fw-bold text-primary mb-1">UTN</h6>
          <small class="text-white-50">Facultad Regional Neuquén</small>
        </div>

        <div class="col-md-4 mb-3 mb-md-0 text-center">
          <small class="d-block text-white-50">© {{ anioActual }} Departamento de Personal</small>
          <small class="d-block text-muted" style="font-size: 0.8rem;">Sistema de Gestión de Licencias</small>
        </div>

        <div class="col-md-4 text-md-end">
          <span class="badge bg-secondary mb-1">v1.0.5</span>
          <div class="small">
            <a href="mailto:soporte@frn.utn.edu.ar" class="text-decoration-none text-light hover-link">
              📧 Soporte Técnico
            </a>
          </div>
        </div>

      </div>
    </div>
  </footer>
</template>

<style scoped>
/* Estilo específico del Footer */
.hover-link:hover {
  color: #0d6efd !important; /* Azul Bootstrap */
  text-decoration: underline !important;
  transition: color 0.3s ease;
}
</style>