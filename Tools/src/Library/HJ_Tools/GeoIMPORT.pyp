<?xml version="1.0" encoding="utf-8"?>
<Element>
	<Script>
		<Name>HJ_Tools\GeoIMPORT.py</Name>
		<Title>GeoIMPORT</Title>
		<Version>0.4</Version>
	</Script>
	<Page>
		<Name>GeoImport</Name>
		<Text>Geodatenimport</Text>
		<Parameter>
			<Name>LaunchRow</Name>
			<Text>Interaktive Karte</Text>
			<ValueType>Row</ValueType>
			<Parameters>
				<Parameter>
					<Name>Launch</Name>
					<Text>Karte öffnen</Text>
					<EventId>1001</EventId>
					<ValueType>Button</ValueType>
				</Parameter>
				<Parameter>
					<Name>Dependencies</Name>
					<Text>Umgebung prüfen</Text>
					<EventId>1004</EventId>
					<ValueType>Button</ValueType>
				</Parameter>
			</Parameters>
		</Parameter>
		<Parameter>
			<Name>ExportFile</Name>
			<Text>Geodaten-Importdatei</Text>
			<Value></Value>
			<ValueType>String</ValueType>
			<ValueDialog>OpenFileDialog</ValueDialog>
			<FileFilter>Geodaten (*.json;*.geojson;*.zip)|*.json;*.geojson;*.zip|</FileFilter>
			<FileExtension>json</FileExtension>
		</Parameter>
		<Parameter>
			<Name>LabelHeight</Name>
			<Text>Schrifthöhe [mm]</Text>
			<Value>2.5</Value>
			<ValueType>Double</ValueType>
			<MinValue>0.5</MinValue>
			<MaxValue>20.0</MaxValue>
		</Parameter>
		<Parameter>
			<Name>SelectedOnly</Name>
			<Text>Nur Grundstücke im Auswahlrahmen</Text>
			<Value>False</Value>
			<ValueType>CheckBox</ValueType>
		</Parameter>
		<Parameter>
			<Name>CheckRow</Name>
			<Text>Export überprüfen</Text>
			<ValueType>Row</ValueType>
			<Parameters>
				<Parameter>
					<Name>Check</Name>
					<Text>Prüfen</Text>
					<EventId>1003</EventId>
					<ValueType>Button</ValueType>
				</Parameter>
			</Parameters>
		</Parameter>
		<Parameter>
			<Name>ImportStatus</Name>
			<Text>Status</Text>
			<Value>GeoJSON mit lokalem Ursprung exportieren.</Value>
			<ValueType>String</ValueType>
			<Enable>False</Enable>
		</Parameter>
	</Page>
</Element>
