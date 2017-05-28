# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AnnotationSaverDockWidget
                                 A QGIS plugin
 Saves annotations to Postgres database
                             -------------------
        begin                : 2017-05-27
        git sha              : $Format:%H$
        copyright            : (C) 2017 by LoreFolk, LLC
        email                : eric@lorefolk.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
import json
import psycopg2
import psycopg2.extras

from PyQt4 import QtGui, uic, QtCore
from PyQt4.QtCore import pyqtSignal, QSettings
from PyQt4.QtGui import QListWidgetItem

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'annotation_saver_dockwidget_base.ui'))

class AnnotationSaverDockWidget(QtGui.QDockWidget, FORM_CLASS): 
    closingPlugin = pyqtSignal()
    table_annotations = 'annotation_layers'
    table_symbol = 'annotation_symbols'
    
    def __init__(self,iface,  parent=None):
        """Constructor."""
        super(AnnotationSaverDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.iface = iface
        self.wdatabaseConnections.addItems(self.getConnections())
        
        self.wdatabaseConnectButton.clicked.connect(self.connectDatabase)
        self.wsaveAnnotationsButton.clicked.connect(self.saveAnnotations)
        self.wfetchAnnotationsButton.clicked.connect(self.fetchAnnotations_click)
        
        self.wlistSchemas.currentIndexChanged.connect(self.wlistSchemas_click)
        self.waddTableButton.clicked.connect(self.waddTableButton_click)
        self.wlistAnnotations.currentItemChanged.connect(self.wlistAnnotations_changed)
        self.layers = self.iface.legendInterface().layers()

    def getPrefix(self):
        return self.waddTablePrefix.displayText() or 'saved' 
    
    def getSchema(self):
        return  self.wlistSchemas.currentText()

    def getLayer(self):
        return  self.wlistLayers.currentText() or ''

    def getTable(self):
        prefix = self.getPrefix()
        return  prefix + '_' + self.table_annotations

    def getAnnotation(self):
        return self.wlistAnnotations.currentItem()

    def saveAnnotations(self):
        annotations = self.collectAnnotations()
        for annotation in annotations:
            data = self.dumpAnnotation(annotation)
            query = self.insertAnnotationQuery(data)
            cur = self.conn.cursor()
            cur.execute(query)
            
        self.conn.commit()
    
    def setDefaultTable(self):
        itemIndex = self.wlistTables.findText(self.table_annotations, QtCore.Qt.MatchContains)
        self.wlistTables.setCurrentIndex(itemIndex)
    
    def setDefaultSchema(self):
        itemIndex = self.wlistSchemas.findText('public')
        self.wlistSchemas.setCurrentIndex(itemIndex)
    
    def setAnnotationText(self, html):
        self.weditAnnotations.setHtml(html)
        self.weditAnnotations.textChanged.connect(self.annotationText_changed)
    
    def annotationText_changed(self):
        html = self.weditAnnotations.toHtml()
        item = self.getAnnotation()
        row = item.data(1)
        row['content'] = html
        item.setData(1, row)
        
    def fetchAnnotations_click(self):
        rows = self.fetchAnnotations()
        self.wlistAnnotations.clear()
        for row in rows:
            item = QListWidgetItem()
            item.setData(1, row)
            item.setText(str(row['fid']))
            self.wlistAnnotations.addItem(item)

    def wlistAnnotations_changed(self, item):
        row = item.data(1)
        print row
        content = row.get('content',  None)
        if content:
            self.setAnnotationText(content)
    
    def fetchAnnotations(self):
        cur = self.conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        layer = self.getLayer()
        table = self.getTable()
        query = """
            SELECT * FROM {table} WHERE layer = '{layer}'
        """.format(table=table, layer=layer)
        print query
        cur.execute(query)
        rows = cur.fetchall()
        
        return rows
    
    def connectDatabase(self):
        conn = self.wdatabaseConnections.currentText()
        self.setConnection(conn)
        self.wlistSchemas.addItems(self.getSchemas())
        self.setDefaultSchema()
        self.setDefaultTable()
        
    def wlistSchemas_click(self, item):
        tables = self.getTables(self.wlistSchemas.currentText())
        self.wlistTables.clear()
        self.wlistTables.addItems(tables)
        
    def waddTableButton_click(self):
        if hasattr(self, 'conn'):
            self.createAnnotationTable()
    
    def collectAnnotations(self):
        items = self.iface.mapCanvas().items()
        annotations = [item for item in items if item.data(0) == 'AnnotationItem']
        return annotations
    
    def dumpSymbolLayer(self, symbol):
        return symbol.properties()
    
    def dumpMarkerSymbol(self, marker):
        return {
            'color':marker.color().name(), 
            'alpha':marker.alpha(), 
            'output_unit': marker.outputUnit(), 
            'angle': marker.angle(), 
            'size': marker.size(), 
            'size_unit': marker.sizeUnit(), 
            'symbol_layers': [self.dumpSymbolLayer(layer) for layer in marker.symbolLayers()]
        }
    
    def dumpAnnotation(self, annotation):
        frame_size = annotation.frameSize()
        ref_offset = annotation.offsetFromReferencePoint()
        map_position_x, map_position_y = annotation.mapPosition()
        crs = annotation.mapPositionCrs()
        marker = annotation.markerSymbol()
        label = annotation.document().toPlainText().replace("'","''")
        label = label[0:256] 
        return {
            "layer": self.getLayer(),
            "srid": crs .postgisSrid(), 
            "label":  label[0:256] , 
            "content": annotation.document().toHtml().replace("'","''"), 
            "frame_color":annotation.frameColor().name(),
            "frame_border_width": annotation.frameBorderWidth(),
            "frame_width": frame_size.width(),
            "frame_height": frame_size.height(),
            "bg_color": annotation.frameBackgroundColor().name(),
            "map_position_x": map_position_x, 
            "map_position_y": map_position_y, 
            "offset_x": ref_offset.x(),
            "offset_y": ref_offset.y(),
            "marker_symbol": json.dumps(self.dumpMarkerSymbol(marker))
        }
    
    def insertAnnotationQuery(self, data, prefix=None, table=None, schema=None):
        schema = schema or self.getSchema()
        prefix = self.getPrefix()
        table = self.table_annotations
        command = """
            INSERT INTO "{schema}"."{prefix}_{table}"
                (
                layer, label, content, srid, map_position_x, map_position_y, 
                frame_color, frame_border_width, frame_width, frame_height,
                bg_color, offset_x, offset_y, 
                marker_symbol
                )
            VALUES('{layer}','{label}', '{content}', '{srid}', '{map_position_x}', '{map_position_y}', 
                '{frame_color}', '{frame_border_width}', '{frame_width}', '{frame_height}',
                '{bg_color}', '{offset_x}', '{offset_y}', 
                '{marker_symbol}');
        """.format(schema=schema,prefix=prefix,table=table, **data)
        return command
        
    def createAnnotationTable(self, prefix=None,  schema=None):
        schema = schema or self.getSchema()
        prefix = self.getPrefix()
        table = self.table_annotations
        command = """
            CREATE TABLE IF NOT EXISTS "{schema}"."{prefix}_{table}" (
                fid SERIAL PRIMARY KEY,
                layer VARCHAR(255),
                content text,
                label VARCHAR(255),
                srid BIGINT,
                map_position_x double precision,
                map_position_y double precision,
                frame_color varchar(10),
                frame_border_width varchar(10),
                frame_width double precision,
                frame_height double precision,
                bg_color varchar(10),
                offset_x double precision,
                offset_y double precision,
                marker_symbol json
            );
        """.format(schema=schema,prefix=prefix,table=table)
        cur = self.conn.cursor()
        cur.execute(command)
        self.conn.commit()
        tables = self.getTables(schema=schema)
        self.wlistTables.clear()
        self.wlistTables.addItems(tables)
        
    def getSchemas(self):
        cur = self.conn.cursor()
        cur.execute("""
            select schema_name
            from information_schema.schemata
        """)
        rows = cur.fetchall()
        self.schemas = [row[0] for row in rows]
        return self.schemas

    def getTables(self, schema=None):
        cur = self.conn.cursor()
        schema = schema or self.getSchema()
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = '%s' AND table_type = 'BASE TABLE'
        """ % (schema, ))
        rows = cur.fetchall()
        self.tables = [row[0] for row in rows]
        return self.tables

    def getConnections(self):
        s = QSettings() 
        s.beginGroup("PostgreSQL/connections")
        currentConnections = s.childGroups()
        s.endGroup()
        return currentConnections

    def setConnection(self,conn):
        s = QSettings()
        s.beginGroup("PostgreSQL/connections/"+conn)
        conn_string = "dbname='%s' user='%s' host='%s' password='%s' port='%i'" % (
            s.value("database", "" ),  
            s.value("username", "" ), 
            s.value("host", "" ),  
            s.value("password", "" ),  
            s.value("port", type=int )
        )
        s.endGroup()          
        print conn_string
        self.conn = psycopg2.connect(conn_string)
        
    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

