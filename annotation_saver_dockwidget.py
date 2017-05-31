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
from PyQt4.QtGui import QListWidgetItem, QColor
from PyQt4.QtCore import pyqtSignal, QSettings, QSizeF, QPointF

from qgis.core import QgsMarkerSymbolV2, QgsSimpleMarkerSymbolLayerV2,  QgsPoint
from qgis.gui import QgsTextAnnotationItem

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
        self.wlistAnnotations.currentItemChanged.connect(self.wlistAnnotations_changed)

        self.waddTableButton.clicked.connect(self.waddTableButton_click)
        self.wplaceAnnotationsButton.clicked.connect(self.wplaceAnnotationsButton_click)
        self.wdeleteAnnotationsButton.clicked.connect(self.wdeleteAnnotationsButton_click)
        
        self.layers = self.iface.legendInterface().layers()
        
        self.annotationBox.setDisabled(True)
        self.addTableBox.setDisabled(True)

    def saveAnnotations(self):
        annotations = self.collectAnnotations()
        for annotation in annotations:
            data = self.dumpAnnotation(annotation)
            query = self.insertAnnotationQuery(data)
            cur = self.conn.cursor()
            cur.execute(query)
            
        self.conn.commit()
        self.fetchAnnotations_click()
   
    def wplaceAnnotationsButton_click(self):
        annotations = self.getSelectedAnnotations()
        for anno in annotations:
            annoData = anno.data(1)
            annotation = QgsTextAnnotationItem(self.iface.mapCanvas())
            
            #Make data accessible from annotation
            annotation.setData(1, annoData) 
            
            doc = annotation.document()
            #"layer": self.getLayer(),
            #"srid": crs.postgisSrid(), 
            #"label":  label[0:256] , 
            
            #"content": annotation.document().toHtml().replace("'","''"), 
            doc.setHtml(annoData.get('content', None))
            annotation.setDocument(doc)
            
            #"frame_color":annotation.frameColor().name(),
            color = QColor()
            color.setNamedColor(annoData.get('frame_color'))
            annotation.setFrameColor(color)
            
             #"bg_color": annotation.frameBackgroundColor().name(),
            color = QColor()
            color.setNamedColor(annoData.get('bg_color'))
            annotation.setFrameBackgroundColor(color)
            
            #"frame_width": frame_size.width(),
            #"frame_height": frame_size.height(),
            size = QSizeF()
            size.setWidth(annoData.get('frame_width'))
            size.setHeight(annoData.get('frame_height'))
            annotation.setFrameSize(size)
            
            #"frame_border_width": annotation.frameBorderWidth(),
            width = float(annoData.get('frame_border_width'))
            annotation.setFrameBorderWidth(width)

            #"map_position_x": map_position_x, 
            #"map_position_y": map_position_y, 
            map_position_x = float(annoData.get('map_position_x'))
            map_position_y = float(annoData.get('map_position_y'))
            annotation.setMapPosition(QgsPoint(map_position_x,map_position_y ))
            
            #"offset_x": ref_offset.x(),
            #"offset_y": ref_offset.y(),
            offset_x = float(annoData.get('offset_x'))
            offset_y = float(annoData.get('offset_y'))
            annotation.setOffsetFromReferencePoint(QPointF(offset_x, offset_y))
            
            #"marker_symbol": json.dumps(self.dumpMarkerSymbol(marker))
            marker_symbol = annoData.get('marker_symbol') 
            
            new_marker_symbol = QgsMarkerSymbolV2()
            #'color':marker.color().name(), 
            color = QColor()
            color.setNamedColor(marker_symbol.get('color'))
            new_marker_symbol.setColor(color)
            
            #'alpha':marker.alpha(), 
            alpha = float(marker_symbol.get('alpha'))
            new_marker_symbol.setAlpha(alpha)

            #'output_unit': marker.outputUnit(), 
            output_unit = marker_symbol.get('output_unit')
            new_marker_symbol.setOutputUnit(output_unit)
            
            #'angle': marker.angle(), 
            angle = float(marker_symbol.get('angle'))
            new_marker_symbol.setAngle(angle)
            
            #'size': marker.size(), 
            size = float(marker_symbol.get('size'))
            new_marker_symbol.setSize(size)
            
            #'size_unit': marker.sizeUnit(), 
            size_unit = marker_symbol.get('size_unit')
            new_marker_symbol.setSizeUnit(size_unit)
            
            #'symbol_layers': [self.dumpSymbolLayer(layer) for layer in marker.symbolLayers()]
            
            for properties in marker_symbol.get('symbol_layers'):
                    print properties
                    #properties = json.loads(properties)
                    new_symbol_layer = QgsSimpleMarkerSymbolLayerV2()
                    new_symbol_layer.restoreDataDefinedProperties(properties)
                    new_marker_symbol.appendSymbolLayer(new_symbol_layer)
    
            annotation.setMarkerSymbol(new_marker_symbol)
            
    def wdeleteAnnotationsButton_click(self):
        annotations = self.getSelectedAnnotations()
        cur = self.conn.cursor()
        for annotation in annotations:
            anno = annotation.data(1)
            command = self.deleteAnnotationQueryByFid(anno.get('fid'))
            cur.execute(command)
        self.conn.commit()
        self.fetchAnnotations_click()
        
    def fetchAnnotations_click(self):
        rows = self.fetchAnnotations()
        self.wlistAnnotations.clear()
        for row in rows:
            item = QListWidgetItem()
            item.setData(1, row)
            item.setText(str(row['label']))
            self.wlistAnnotations.addItem(item)
   
    def fetchAnnotations(self):
        cur = self.conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        layer = self.getLayer()
        table = self.getTable()
        query = """
            SELECT * FROM {table} WHERE layer = '{layer}'
        """.format(table=table, layer=layer)
        cur.execute(query)
        rows = cur.fetchall()
        return rows

    def setAnnotationText(self, html):
        self.weditAnnotations.setHtml(html)
        self.weditAnnotations.textChanged.connect(self.annotationText_changed)
    
    def annotationText_changed(self):
        html = self.weditAnnotations.toHtml()
        item = self.getAnnotation()
        row = item.data(1)
        row['content'] = html
        item.setData(1, row)

    def wlistAnnotations_changed(self, item):
        #row = item.data(1)
        #content = row.get('content',  None)
        pass

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
    
    def connectDatabase(self):
        conn = self.wdatabaseConnections.currentText()
        self.setConnection(conn)
        self.wlistSchemas.addItems(self.getSchemas())
        self.setDefaultSchema()
        self.setDefaultTable()
        self.annotationBox.setDisabled(False)
        self.addTableBox.setDisabled(False)

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

    def deleteAnnotationQueryByFid(self, fid, prefix=None, table=None, schema=None):
        schema = schema or self.getSchema()
        prefix = self.getPrefix()
        table = self.table_annotations
        command = """
            DELETE FROM "{schema}"."{prefix}_{table}"
                WHERE fid = {fid};
        """.format(schema=schema,prefix=prefix,table=table, fid=fid)
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
        self.setDefaultTable()
        
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
        self.conn = psycopg2.connect(conn_string)

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
    
    def getSelectedAnnotations(self):
        return self.wlistAnnotations.selectedItems()
    
    def setDefaultTable(self):
        itemIndex = self.wlistTables.findText(self.table_annotations, QtCore.Qt.MatchContains)
        self.wlistTables.setCurrentIndex(itemIndex)
    
    def setDefaultSchema(self):
        itemIndex = self.wlistSchemas.findText('public')
        self.wlistSchemas.setCurrentIndex(itemIndex)
        
    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

