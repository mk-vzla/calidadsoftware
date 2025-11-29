from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password
import re


# ------------------------
#  Modelo Usuario
# ------------------------
class Usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    nombres = models.CharField(max_length=100)
    usuario = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)

    # Contraseña hasheada (segura)
    password = models.CharField(max_length=255)

    # Seguridad
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    ultimo_login = models.DateTimeField(null=True, blank=True)

    def set_password(self, raw_password):
        """Hashea y guarda la contraseña."""
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """Compara una contraseña sin hash con el hash guardado."""
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.usuario


# ------------------------
#  Modelo Categoría
# ------------------------
class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre


# ------------------------
#  Validadores personalizados
# ------------------------
def validar_codigo_producto(value):
    """
    Código debe tener formato:
      - 1 letra inicial del producto
      - 3 dígitos correlativos
    Ejemplo: M001, A015, H300
    """
    patron = r'^[A-Z][0-9]{3}$'
    if not re.match(patron, value):
        raise ValidationError(
            "El código debe comenzar con una letra y contener 3 dígitos. Ej.: M001"
        )


# ------------------------
#  Modelo Producto
# ------------------------
class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True)

    codigo_producto = models.CharField(
        max_length=4,
        unique=True,
        validators=[validar_codigo_producto],
        help_text="Formato: Letra + 3 dígitos (ej: M001)"
    )

    nombre = models.CharField(max_length=200, unique=True)
    descripcion = models.TextField()
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    precio = models.IntegerField()
    cantidad = models.IntegerField(default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(precio__gte=0),
                name="precio_no_negativo"
            )
        ]

    def __str__(self):
        return f"{self.codigo_producto} - {self.nombre}"


# ------------------------
#  Modelo Movimiento Inventario
# ------------------------
class MovimientoInventario(models.Model):
    TIPO_MOV = [
        ("ALTA", "Alta"),
        ("BAJA", "Baja"),
        ("MODI", "Modificación"),
    ]

    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)
    cantidad = models.IntegerField()
    # Campos redundantes para auditoría: se rellenan al crear el movimiento
    producto_nombre = models.CharField(max_length=200, null=True, blank=True)
    producto_codigo = models.CharField(max_length=10, null=True, blank=True)
    tipo = models.CharField(max_length=8, choices=TIPO_MOV)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        # Mostrar el nombre ya guardado si existe, sino el relacionado (o '(eliminado)')
        if self.producto_nombre:
            prod_nombre = self.producto_nombre
        else:
            prod_nombre = self.producto.nombre if self.producto else '(eliminado)'
        return f"{self.tipo} | {prod_nombre} | {self.cantidad}"


# ------------------------
#  Modelo Stock
# ------------------------
class Stock(models.Model):
    producto = models.OneToOneField(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(cantidad__gte=0),
                name="stock_no_negativo"
            )
        ]

    def __str__(self):
        return f"{self.producto.nombre}: {self.cantidad}"
