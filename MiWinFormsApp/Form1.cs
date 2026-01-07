using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Windows.Forms;

namespace MiWinFormsApp
{
    public partial class Form1 : Form
    {
        private TextBox txtUser;
        private TextBox txtPassword;
        private Button btnGo;
        private TextBox txtLog;
        private Label lblStatus;

        public Form1()
        {
            InitializeComponent();

            BuildUi();
            WireEvents();
            ApplyDarkTheme(this);

            Log("UI lista. Esperando acción.");
        }

        // ==========================
        // UI
        // ==========================
        private void BuildUi()
        {
            Text = "Scrapper UI (Python + Selenium)";
            StartPosition = FormStartPosition.CenterScreen;
            Size = new Size(820, 520);
            MinimumSize = new Size(760, 480);
            Font = new Font("Segoe UI", 10);

            var lblTitle = new Label
            {
                Text = "Panel de Scrapper",
                Font = new Font("Segoe UI", 16, FontStyle.Bold),
                AutoSize = true,
                Location = new Point(20, 15)
            };

            var lblSubtitle = new Label
            {
                Text = "Control de Selenium vía Python",
                AutoSize = true,
                Location = new Point(22, 52)
            };

            var grpLogin = new GroupBox
            {
                Text = "Credenciales",
                Location = new Point(20, 85),
                Size = new Size(360, 160)
            };

            grpLogin.Controls.Add(new Label
            {
                Text = "Usuario:",
                AutoSize = true,
                Location = new Point(18, 35)
            });

            txtUser = new TextBox
            {
                Location = new Point(18, 58),
                Width = 320
            };

            grpLogin.Controls.Add(txtUser);

            grpLogin.Controls.Add(new Label
            {
                Text = "Password:",
                AutoSize = true,
                Location = new Point(18, 92)
            });

            txtPassword = new TextBox
            {
                Location = new Point(18, 115),
                Width = 320,
                UseSystemPasswordChar = true
            };

            grpLogin.Controls.Add(txtPassword);

            var grpActions = new GroupBox
            {
                Text = "Acciones",
                Location = new Point(400, 85),
                Size = new Size(390, 160)
            };

            btnGo = new Button
            {
                Text = "Ir a la página",
                Location = new Point(18, 40),
                Size = new Size(160, 40)
            };

            lblStatus = new Label
            {
                Text = "Estado: Idle",
                AutoSize = true,
                Location = new Point(200, 52)
            };

            grpActions.Controls.Add(btnGo);
            grpActions.Controls.Add(lblStatus);

            var grpLog = new GroupBox
            {
                Text = "Log del Scrapper",
                Location = new Point(20, 260),
                Size = new Size(770, 200)
            };

            txtLog = new TextBox
            {
                Multiline = true,
                ReadOnly = true,
                ScrollBars = ScrollBars.Vertical,
                Location = new Point(14, 30),
                Size = new Size(742, 155),
                Font = new Font("Consolas", 10)
            };

            grpLog.Controls.Add(txtLog);

            Controls.Add(lblTitle);
            Controls.Add(lblSubtitle);
            Controls.Add(grpLogin);
            Controls.Add(grpActions);
            Controls.Add(grpLog);
        }

        private void WireEvents()
        {
            btnGo.Click += (_, __) => RunPythonScrapper();
        }

        // ==========================
        // PYTHON INTEGRATION
        // ==========================
        private void RunPythonScrapper()
        {
            if (string.IsNullOrWhiteSpace(txtUser.Text))
            {
                MessageBox.Show("Ingresa el usuario.", "Falta usuario",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            SetStatus("Ejecutando scrapper...");
            Log("Lanzando Python + Selenium...");

            // Volver desde bin/Debug/netX al root del proyecto
            var projectRoot = Path.GetFullPath(
                Path.Combine(AppDomain.CurrentDomain.BaseDirectory, @"..\..\..\")
            );

            var psi = new ProcessStartInfo
            {
                FileName = "python",
                Arguments = $"web_scrapper.py login {txtUser.Text}",
                WorkingDirectory = projectRoot,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            var process = new Process { StartInfo = psi };

            process.OutputDataReceived += (_, e) =>
            {
                if (e.Data != null)
                    Invoke(() => Log(e.Data));
            };

            process.ErrorDataReceived += (_, e) =>
            {
                if (e.Data != null)
                    Invoke(() => Log("[ERROR] " + e.Data));
            };

            process.EnableRaisingEvents = true;
            process.Exited += (_, __) =>
            {
                Invoke(() => SetStatus("Proceso finalizado"));
            };

            process.Start();
            process.BeginOutputReadLine();
            process.BeginErrorReadLine();
        }

        // ==========================
        // LOG & STATUS
        // ==========================
        private void Log(string message)
        {
            txtLog.AppendText($"[{DateTime.Now:HH:mm:ss}] {message}{Environment.NewLine}");
        }

        private void SetStatus(string status)
        {
            lblStatus.Text = $"Estado: {status}";
        }

        // ==========================
        // DARK THEME
        // ==========================
        private void ApplyDarkTheme(Control root)
        {
            BackColor = Color.FromArgb(30, 30, 30);
            ForeColor = Color.Gainsboro;
            ApplyRecursive(root);
        }

        private void ApplyRecursive(Control control)
        {
            if (control is GroupBox)
            {
                control.BackColor = Color.FromArgb(37, 37, 38);
                control.ForeColor = Color.Gainsboro;
            }
            else if (control is TextBox txt)
            {
                txt.BackColor = Color.FromArgb(45, 45, 48);
                txt.ForeColor = Color.Gainsboro;
                txt.BorderStyle = BorderStyle.FixedSingle;
            }
            else if (control is Button btn)
            {
                btn.BackColor = Color.FromArgb(58, 61, 65);
                btn.ForeColor = Color.White;
                btn.FlatStyle = FlatStyle.Flat;
                btn.FlatAppearance.BorderColor = Color.FromArgb(63, 63, 70);

                btn.MouseEnter += (_, __) =>
                    btn.BackColor = Color.FromArgb(80, 83, 87);

                btn.MouseLeave += (_, __) =>
                    btn.BackColor = Color.FromArgb(58, 61, 65);
            }
            else if (control is Label)
            {
                control.ForeColor = Color.Gainsboro;
            }

            foreach (Control child in control.Controls)
                ApplyRecursive(child);
        }
    }
}
