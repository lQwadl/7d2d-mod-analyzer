using System;
using System.Diagnostics;
using System.IO;

namespace ModManager.Backend.Services
{
    public static class PortLogger
    {
        private static readonly object _gate = new object();

        public static void Info(string message) => Write("INFO", message);
        public static void Warn(string message) => Write("WARN", message);
        public static void Error(string message, Exception? ex = null)
        {
            var full = ex is null ? message : message + " | " + ex.GetType().Name + ": " + ex.Message;
            Write("ERROR", full);
        }

        private static void Write(string level, string message)
        {
            var line = $"[{DateTime.UtcNow:O}] {level} {message}";

            try
            {
                Debug.WriteLine(line);
                Trace.WriteLine(line);
            }
            catch
            {
                // ignore debug/trace failures
            }

            try
            {
                lock (_gate)
                {
                    var baseDir = AppContext.BaseDirectory;
                    var logDir = Path.Combine(baseDir, "logs");
                    Directory.CreateDirectory(logDir);
                    var path = Path.Combine(logDir, "backend.log");
                    File.AppendAllText(path, line + Environment.NewLine);
                }
            }
            catch
            {
                // never fail port execution due to logging
            }
        }
    }
}
