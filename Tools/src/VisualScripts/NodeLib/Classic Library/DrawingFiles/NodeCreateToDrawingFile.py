"""Allplan 2027 Visual Scripting: choose a safe target drawing file.

Selected target is stored in the *existing* FileNumber output parameter.
No hidden DrawingFile attribute is accessed: VS did not provide that attribute.
"""
import NemAll_Python_BaseElements as Allplan_BaseElements
import NemAll_Python_Geometry as Allplan_Geo
import NemAll_Python_Utility as Allplan_Util
from NodeUtil.NodeBase import NodeBase
from NodeUtil import NodeObjectUtil

import clr

clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")

from System.Windows import (
    Window,
    Thickness,
    WindowStartupLocation,
    ResizeMode,
    TextWrapping,
    HorizontalAlignment,
    MessageBox,
    MessageBoxButton,
    MessageBoxImage
)
from System.Windows.Controls import StackPanel, TextBlock, Button, Orientation


def create_node(init_data):
    return NodeDrawingFileSelection(init_data)


class NodeDrawingFileSelection(NodeBase):
    @staticmethod
    def _active_number():
        return int(Allplan_BaseElements.DrawingFileService.GetActiveFileNumber())

    @classmethod
    def _writable_background(cls):
        active = cls._active_number()
        result = []
        for number, state in Allplan_BaseElements.DrawingFileService().GetFileState():
            try:
                if (state == Allplan_BaseElements.DrawingFileLoadState.ActiveBackground
                        and int(number) > 0 and int(number) != active):
                    result.append(int(number))
            except (TypeError, ValueError):
                continue
        return sorted(set(result))

    @staticmethod
    def _selected(value):
        values = value if isinstance(value, (list, tuple)) else [value]
        for candidate in values:
            try:
                number = int(candidate)
                if number > 0:
                    return number
            except (TypeError, ValueError):
                continue
        return 0

    def _status(self, message):
        self.build_ele.SelectionHint.value = str(message)

    def on_control_event(self, event_id):
        """ Handle the button event """

        if event_id == 100:
            self.export_elements()



    def show_export_dialog(self, file_number):
        """Zeigt den WPF-Dialog an.

        Rückgabe: overwrite, add oder cancel.
        """

        result = ["cancel"]


        window = Window()
        window.Title = "Teilbild überschreiben?"
        window.Width = 460
        window.Height = 210
        window.ResizeMode = ResizeMode.NoResize
        window.WindowStartupLocation = WindowStartupLocation.CenterScreen
        window.Topmost = True
        window.ShowInTaskbar = False

        layout = StackPanel()
        layout.Margin = Thickness(20)

        message = TextBlock()
        message.Text = (
            f"Teilbild {file_number} enthält bereits Objekte.\n\n"
            "Objekte ersetzen?"
        )
        message.TextWrapping = TextWrapping.Wrap
        message.Margin = Thickness(0, 0, 0, 20)
        layout.Children.Add(message)

        buttons = StackPanel()
        buttons.Orientation = Orientation.Horizontal
        buttons.HorizontalAlignment = HorizontalAlignment.Center


        def make_button(caption, value):
            button = Button()
            button.Content = caption
            button.Width = 115
            button.Height = 32
            button.Margin = Thickness(4)

            def clicked(sender, args):
                result[0] = value
                window.Close()

            button.Click += clicked
            buttons.Children.Add(button)

        make_button("Ja", "overwrite")
        make_button("Hinzufügen", "add")
        make_button("Abbrechen", "cancel")

        layout.Children.Add(buttons)
        window.Content = layout

        print("WPF-Dialog wird geöffnet")

        window.ShowDialog()

        print("Dialogauswahl:", result[0])
        return result[0]



    def export_elements(self):
        """Export to selected DrawingFile(s)"""

        build_ele = self.build_ele

        file_numbers = build_ele.FileNumbers.value

        if isinstance(file_numbers, int):
            file_numbers = [file_numbers]

        elements = NodeObjectUtil.create_objects_list(build_ele.Elements.value)


        if not file_numbers or file_numbers == [0] or file_numbers == 0:
            MessageBox.Show(
                "Es wurde kein Ziel-Teilbild ausgewählt.\n\n"
                "Bitte wähle zuerst ein Teilbild aus.",
                "Export nicht möglich",
                MessageBoxButton.OK,
                MessageBoxImage.Warning
            )
            return


        if not elements:
            self.error = "Keine Objekte zum erstellen gefunden"
            return

        drawing_file_serv = Allplan_BaseElements.DrawingFileService()
        previous_states = drawing_file_serv.GetFileState()
        original_active_file = (Allplan_BaseElements.DrawingFileService.GetActiveFileNumber())

        insert_mat = Allplan_Geo.Matrix3D()

        try:
            for file_number in file_numbers:

                file_number = int(file_number)


                if file_number == original_active_file:
                    MessageBox.Show(
                        f"Das Teilbild {file_number} ist aktuell aktiv.\n\n"
                        "Ein Export in das aktive Teilbild ist nicht erlaubt, "
                        "um das PythonPart vor unbeabsichtigten "
                        "Änderungen zu schützen.\n\n"
                        "Bitte wähle ein anderes Teilbild aus.",
                        "Export nicht möglich",
                        MessageBoxButton.OK,
                        MessageBoxImage.Warning
                    )
                    continue





                drawing_file_serv.UnloadAll(self.document)

                drawing_file_serv.LoadFile(
                    self.document,
                    file_number,
                    Allplan_BaseElements.DrawingFileLoadState.ActiveForeground
                )


                existing_elements = (
                    Allplan_BaseElements.ElementsSelectService
                    .SelectAllElements(self.document)
                )

                if len(existing_elements) > 0:

                    response = self.show_export_dialog(file_number)

                    if response == "cancel":
                        continue

                    elif response == "overwrite":
                        Allplan_BaseElements.DeleteElements(
                            self.document,
                            existing_elements
                        )

                    elif response == "add":
                        pass




                Allplan_BaseElements.CreateElements(
                    self.document,
                    insert_mat,
                    elements,
                    [],
                    None
                )

        finally:
            drawing_file_serv.UnloadAll(self.document)

            valid_states = (
                Allplan_BaseElements.DrawingFileLoadState.PassiveBackground,
                Allplan_BaseElements.DrawingFileLoadState.ActiveBackground,
                Allplan_BaseElements.DrawingFileLoadState.ActiveForeground
            )

            for number, state in previous_states:
                if state not in valid_states:
                    print(
                        f"Teilbild {number}:"
                        f"Ungültiger Status {state}, wird übersprungen"
                    )
                    continue

                drawing_file_serv.LoadFile(
                    self.document,
                    number,
                    state
                )

        # Ursprüngliche Teilbilder wiederherstellen
        for number, state in previous_states:
            if state not in valid_states:
                continue

            drawing_file_serv.LoadFile(
                self.document,
                number,
                state
            )

        # Grafische Darstellung aktualisieren
        Allplan_BaseElements.DrawingService.RedrawAll(
            self.document
        )

    def _create_output(self):

        return True
