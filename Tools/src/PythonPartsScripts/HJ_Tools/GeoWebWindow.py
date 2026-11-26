"""Modal WPF/WebView2 window in the ALLPLAN process (Windows only).

No remote host objects: web messages carry only an export job identifier.
No ALLPLAN geometry API is called from the window's UI thread.
"""
from pathlib import Path
import re
import json
import os
import tempfile


def show_map(url, prg):
    import clr
    clr.AddReference("WindowsBase")
    clr.AddReference("PresentationCore")
    clr.AddReference("PresentationFramework")
    for name in ("Microsoft.Web.WebView2.Core", "Microsoft.Web.WebView2.Wpf"):
        path = Path(prg) / (name + ".dll")
        if not path.is_file():
            matches = list(Path(prg).glob("*/" + name + ".dll"))
            if len(matches) != 1:
                raise RuntimeError(f"WebView2-Bibliothek fehlt: {name}")
            path = matches[0]
        clr.AddReference(str(path))
    from System import Uri, UriPartial
    from System.Threading import Thread, ThreadStart, ApartmentState
    from System.Windows import Window, WindowStartupLocation
    from System.Windows.Threading import Dispatcher
    from Microsoft.Web.WebView2.Wpf import WebView2, CoreWebView2CreationProperties

    result = {"job": None, "error": None}

    def run():
        view = None
        try:
            window = Window()
            window.Title = "HJ Tools | GeoIMPORT"
            window.Width = 1350
            window.Height = 880
            window.MinWidth = 800
            window.MinHeight = 550
            window.WindowStartupLocation = WindowStartupLocation.CenterScreen
            view = WebView2()
            properties = CoreWebView2CreationProperties()
            properties.UserDataFolder = str(Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "HJ_Tools" / "GeoIMPORT" / "WebView2")
            view.CreationProperties = properties
            window.Content = view

            def initialized(sender, args):
                if not args.IsSuccess:
                    result["error"] = str(args.InitializationException)
                    window.Close()
                    return
                core = view.CoreWebView2
                core.Settings.AreHostObjectsAllowed = False
                core.Settings.AreDevToolsEnabled = False
                core.Settings.IsWebMessageEnabled = True

                def navigating(_sender, event):
                    address = Uri(event.Uri)
                    expected = Uri(url)
                    if address.GetLeftPart(UriPartial.Authority) != expected.GetLeftPart(UriPartial.Authority):
                        event.Cancel = True

                def popup(_sender, event):
                    event.Handled = True

                def message(_sender, event):
                    if str(event.Source).rstrip("/") != url.rstrip("/"):
                        return
                    try:
                        raw = str(event.WebMessageAsJson)
                        if len(raw) > 256:
                            return
                        data = json.loads(raw)
                        job = data.get("job", "")
                        if data.get("action") == "importGeodata" and re.fullmatch(r"[a-f0-9]{32}", job):
                            result["job"] = job
                            window.Close()
                    except (ValueError, TypeError, AttributeError):
                        return

                core.NavigationStarting += navigating
                core.NewWindowRequested += popup
                core.WebMessageReceived += message
                core.Navigate(url)

            view.CoreWebView2InitializationCompleted += initialized
            # Setting Source triggers asynchronous initialization.
            # Use a blank local page first; navigation begins in initialized().
            def loaded(_sender, _args):
                try:
                    view.EnsureCoreWebView2Async(None)
                except Exception as exc:
                    result["error"] = str(exc)
                    window.Close()

            window.Loaded += loaded
            window.ShowDialog()
        except Exception as exc:
            result["error"] = str(exc)
        finally:
            if view is not None:
                view.Dispose()

    if Thread.CurrentThread.GetApartmentState() == ApartmentState.STA:
        run()
    else:
        def on_sta():
            try:
                run()
            finally:
                Dispatcher.CurrentDispatcher.InvokeShutdown()
        thread = Thread(ThreadStart(on_sta))
        thread.SetApartmentState(ApartmentState.STA)
        thread.Start()
        thread.Join()
    if result["error"]:
        raise RuntimeError(result["error"])
    return result["job"]
