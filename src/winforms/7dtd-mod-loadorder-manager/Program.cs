using System;
using System.Windows.Forms;
using ModManagerPrototype;

namespace SevenDays.ModManager
{
    internal static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.SetHighDpiMode(HighDpiMode.SystemAware);
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            try
            {
                ModManagerPrototype.PortTestRunner.RunTests().GetAwaiter().GetResult();
            }
            catch
            {
                // Never block UI startup due to test harness failures.
            }

            var form = new Form1();
            Form1BackendHost.Wire(form);
            Application.Run(form);
        }
    }
}
