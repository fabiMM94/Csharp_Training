using System;
using System.Reflection.Emit;
using System.Windows.Forms;
using static System.Net.Mime.MediaTypeNames;

namespace AppSaludo
{
    public class Form1 : Form
    {
        private TextBox txtNombre;
        private Button btnSaludar;
        private Label lblResultado;

        public Form1()
        {
            // Configuración de la ventana
            Text = "App Saludo";
            Width = 400;
            Height = 200;

            // TextBox
            txtNombre = new TextBox
            {
                Left = 20,
                Top = 20,
                Width = 200
            };

            // Botón
            btnSaludar = new Button
            {
                Left = 240,
                Top = 18,
                Width = 120,
                Text = "Saludar"
            };

            // Label
            lblResultado = new Label
            {
                Left = 20,
                Top = 60,
                Width = 340,
                Text = "Aquí aparecerá el saludo"
            };

            // Evento del botón
            btnSaludar.Click += BtnSaludar_Click;

            // Agregar controles a la ventana
            Controls.Add(txtNombre);
            Controls.Add(btnSaludar);
            Controls.Add(lblResultado);
        }

        private void BtnSaludar_Click(object sender, EventArgs e)
        {
            string nombre = txtNombre.Text;

            if (string.IsNullOrWhiteSpace(nombre))
                lblResultado.Text = "Por favor escribe tu nombre.";
            else
                lblResultado.Text = $"Hola, {nombre} 👋";
        }
    }
}
