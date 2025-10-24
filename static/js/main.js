// Menú responsive
const menuToggle = document.getElementById('mobile-menu');
const navLinks = document.querySelector('.nav-links');

menuToggle.addEventListener('click', () => {
    navLinks.classList.toggle('active');
    menuToggle.classList.toggle('open');
});

// Simulación de carrito
function agregarAlCarrito(id) {
    alert("Producto " + id + " agregado al carrito!");
}
