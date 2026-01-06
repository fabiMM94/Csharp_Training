
// See https://aka.ms/new-console-template for more information
/*
using System.Globalization;
using static System.Net.Mime.MediaTypeNames;

string nombre = "Fabian";
String edad = "31";
DateTime fechaActual = DateTime.Now;
Console.WriteLine("Hello, World!");
Console.WriteLine(30+40);
Console.WriteLine("Fecha actual es:" + fechaActual);
Console.WriteLine($"nombre de usuario: {nombre}, edad {edad}");
Console.ReadKey();

*/
using System;
using System.Windows.Forms;

namespace AppSaludo
{
    internal static class Program
    {
        [STAThread]
        static void Main()
        {
            ApplicationConfiguration.Initialize();
            Application.Run(new Form1());
        }
    }
}