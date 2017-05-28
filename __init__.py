# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AnnotationSaver
                                 A QGIS plugin
 Saves annotations to Postgres database
                             -------------------
        begin                : 2017-05-27
        copyright            : (C) 2017 by LoreFolk, LLC
        email                : eric@lorefolk.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load AnnotationSaver class from file AnnotationSaver.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .annotation_saver import AnnotationSaver
    return AnnotationSaver(iface)
