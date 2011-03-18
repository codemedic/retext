#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2011 Dmitry Shachnev

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.

import sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *

import markdown
md = markdown.Markdown(['footnotes', 'tables'])

try:
	import gdata.docs
	import gdata.docs.service
	from gdata import MediaSource
except:
	use_gdocs = False
else:
	use_gdocs = True

app_name = "ReText"
app_version = "0.5.2 beta"

icon_path = "icons/"

class HtmlHighlighter(QSyntaxHighlighter):
	def __init__(self, parent):
		QSyntaxHighlighter.__init__(self, parent)
	
	def highlightBlock(self, text):
		charFormat = QTextCharFormat()
		patterns = ("<[^>]*>", "&[^; ]*;", "\"[^\"]*\"", "<!--[^-->]*-->")
		foregrounds = [Qt.darkMagenta, Qt.darkCyan, Qt.darkYellow, Qt.gray]
		for i in range(len(patterns)):
			expression = QRegExp(patterns[i])
			index = expression.indexIn(text)
			if i == 3:
				charFormat.setFontWeight(QFont.Normal)
			else:
				charFormat.setFontWeight(QFont.Bold)
			charFormat.setForeground(foregrounds[i])
			while (index >= 0):
				length = expression.matchedLength()
				self.setFormat(index, length, charFormat)
				index = expression.indexIn(text, index + length)

class LogPassDialog(QDialog):
	def __init__(self, defaultLogin="", defaultPass=""):
		QDialog.__init__(self)
		self.setWindowTitle(app_name)
		self.verticalLayout = QVBoxLayout(self)
		self.label = QLabel(self)
		self.label.setText(self.tr("Enter your Google account data"))
		self.verticalLayout.addWidget(self.label)
		self.loginEdit = QLineEdit(self)
		self.loginEdit.setText(defaultLogin)
		self.verticalLayout.addWidget(self.loginEdit)
		self.passEdit = QLineEdit(self)
		self.passEdit.setText(defaultPass)
		self.passEdit.setEchoMode(QLineEdit.Password)
		try:
			self.loginEdit.setPlaceholderText(self.tr("Username"))
			self.passEdit.setPlaceholderText(self.tr("Password"))
		except:
			pass
		self.verticalLayout.addWidget(self.passEdit)
		self.buttonBox = QDialogButtonBox(self)
		self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
		self.verticalLayout.addWidget(self.buttonBox)
		self.connect(self.buttonBox, SIGNAL("accepted()"), self.accept)
		self.connect(self.buttonBox, SIGNAL("rejected()"), self.reject)

class HtmlDialog(QDialog):
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		self.resize(600, 500)
		self.verticalLayout = QVBoxLayout(self)
		self.textEdit = QTextEdit(self)
		self.textEdit.setReadOnly(True)
		monofont = QFont()
		monofont.setFamily('monospace')
		self.textEdit.setFont(monofont)
		self.syntaxHighlighter = HtmlHighlighter(self.textEdit.document())
		self.verticalLayout.addWidget(self.textEdit)
		self.buttonBox = QDialogButtonBox(self)
		self.buttonBox.setOrientation(Qt.Horizontal)
		self.buttonBox.setStandardButtons(QDialogButtonBox.Close)
		self.connect(self.buttonBox, SIGNAL("clicked(QAbstractButton*)"), self.doClose)
		self.verticalLayout.addWidget(self.buttonBox)
	
	def doClose(self):
		self.close()

class ReTextWindow(QMainWindow):
	def __init__(self, parent=None):
		QMainWindow.__init__(self, parent)
		self.resize(800, 600)
		screen = QDesktopWidget().screenGeometry()
		size = self.geometry()
		self.move((screen.width()-size.width())/2, (screen.height()-size.height())/2)
		self.setWindowTitle(self.tr('New document') + '[*] ' + QChar(0x2014) + ' ' + app_name)
		if QFile.exists(icon_path+'retext.png'):
			self.setWindowIcon(QIcon(icon_path+'retext.png'))
		else:
			self.setWindowIcon(QIcon.fromTheme('retext', QIcon.fromTheme('accessories-text-editor')))
		self.centralwidget = QWidget(self)
		self.verticalLayout = QVBoxLayout(self.centralwidget)
		self.previewBox = QTextEdit(self.centralwidget)
		self.previewBox.setVisible(False)
		self.previewBox.setReadOnly(True)
		self.verticalLayout.addWidget(self.previewBox)
		self.editBox = QTextEdit(self.centralwidget)
		self.editBox.setAcceptRichText(False)
		monofont = QFont()
		monofont.setFamily('monospace')
		self.editBox.setFont(monofont)
		self.verticalLayout.addWidget(self.editBox)
		self.setCentralWidget(self.centralwidget)
		self.syntaxHighlighter = HtmlHighlighter(self.editBox.document())
		self.toolBar = QToolBar(self.tr('File toolbar'), self)
		self.addToolBar(Qt.TopToolBarArea, self.toolBar)
		self.editBar = QToolBar(self.tr('Edit toolbar'), self)
		self.addToolBar(Qt.TopToolBarArea, self.editBar)
		self.actionNew = QAction(QIcon.fromTheme('document-new', QIcon(icon_path+'document-new.png')), self.tr('New'), self)
		self.actionNew.setShortcut(QKeySequence.New)
		self.connect(self.actionNew, SIGNAL('triggered()'), self.createNew)
		self.actionOpen = QAction(QIcon.fromTheme('document-open', QIcon(icon_path+'document-open.png')), self.tr('Open'), self)
		self.actionOpen.setShortcut(QKeySequence.Open)
		self.actionOpen.setPriority(QAction.LowPriority)
		self.connect(self.actionOpen, SIGNAL('triggered()'), self.openFile)
		self.actionSave = QAction(QIcon.fromTheme('document-save', QIcon(icon_path+'document-save.png')), self.tr('Save'), self)
		self.actionSave.setEnabled(False)
		self.actionSave.setShortcut(QKeySequence.Save)
		self.actionSave.setPriority(QAction.LowPriority)
		self.connect(self.editBox.document(), SIGNAL('modificationChanged(bool)'), self.modificationChanged)
		self.connect(self.actionSave, SIGNAL('triggered()'), self.saveFile)
		self.actionSaveAs = QAction(QIcon.fromTheme('document-save-as', QIcon(icon_path+'document-save-as.png')), self.tr('Save as'), self)
		self.actionSaveAs.setShortcut(QKeySequence.SaveAs)
		self.connect(self.actionSaveAs, SIGNAL('triggered()'), self.saveFileAs)
		self.actionPrint = QAction(QIcon.fromTheme('document-print', QIcon(icon_path+'document-print.png')), self.tr('Print'), self)
		self.actionPrint.setShortcut(QKeySequence.Print)
		self.actionPrint.setPriority(QAction.LowPriority)
		self.connect(self.actionPrint, SIGNAL('triggered()'), self.printFile)
		self.actionPrintPreview = QAction(QIcon.fromTheme('document-print-preview', QIcon(icon_path+'document-print-preview.png')), self.tr('Print preview'), self)
		self.connect(self.actionPrintPreview, SIGNAL('triggered()'), self.printPreview)
		self.actionViewHtml = QAction(QIcon.fromTheme('text-html', QIcon(icon_path+'text-html.png')), self.tr('View HTML code'), self)
		self.connect(self.actionViewHtml, SIGNAL('triggered()'), self.viewHtml)
		self.actionPreview = QAction(QIcon.fromTheme('x-office-document', QIcon(icon_path+'x-office-document.png')), self.tr('Preview'), self)
		self.actionPreview.setCheckable(True)
		self.connect(self.actionPreview, SIGNAL('triggered(bool)'), self.preview)
		self.actionPerfectHtml = QAction(QIcon.fromTheme('text-html', QIcon(icon_path+'text-html.png')), 'HTML', self)
		self.connect(self.actionPerfectHtml, SIGNAL('triggered()'), self.saveFilePerfect)
		self.actionPdf = QAction(QIcon.fromTheme('application-pdf', QIcon(icon_path+'application-pdf.png')), 'PDF', self)
		self.connect(self.actionPdf, SIGNAL('triggered()'), self.savePdf)
		self.actionOdf = QAction(QIcon.fromTheme('x-office-document', QIcon(icon_path+'x-office-document.png')), 'ODT', self)
		self.connect(self.actionOdf, SIGNAL('triggered()'), self.saveOdf)
		self.actionQuit = QAction(QIcon.fromTheme('application-exit', QIcon(icon_path+'application-exit.png')), self.tr('Quit'), self)
		self.actionQuit.setShortcut(QKeySequence.Quit)
		self.actionQuit.setMenuRole(QAction.QuitRole)
		self.connect(self.actionQuit, SIGNAL('triggered()'), qApp, SLOT('quit()'))
		self.actionUndo = QAction(QIcon.fromTheme('edit-undo', QIcon(icon_path+'edit-undo.png')), self.tr('Undo'), self)
		self.actionUndo.setShortcut(QKeySequence.Undo)
		self.actionRedo = QAction(QIcon.fromTheme('edit-redo', QIcon(icon_path+'edit-redo.png')), self.tr('Redo'), self)
		self.actionRedo.setShortcut(QKeySequence.Redo)
		self.connect(self.actionUndo, SIGNAL('triggered()'), self.editBox, SLOT('undo()'))
		self.connect(self.actionRedo, SIGNAL('triggered()'), self.editBox, SLOT('redo()'))
		self.actionUndo.setEnabled(False)
		self.actionRedo.setEnabled(False)
		self.connect(self.editBox.document(), SIGNAL('undoAvailable(bool)'), self.actionUndo, SLOT('setEnabled(bool)'))
		self.connect(self.editBox.document(), SIGNAL('redoAvailable(bool)'), self.actionRedo, SLOT('setEnabled(bool)'))
		self.actionCopy = QAction(QIcon.fromTheme('edit-copy', QIcon(icon_path+'edit-copy.png')), self.tr('Copy'), self)
		self.actionCopy.setShortcut(QKeySequence.Copy)
		self.actionCopy.setEnabled(False)
		self.actionCut = QAction(QIcon.fromTheme('edit-cut', QIcon(icon_path+'edit-cut.png')), self.tr('Cut'), self)
		self.actionCut.setShortcut(QKeySequence.Cut)
		self.actionCut.setEnabled(False)
		self.actionPaste = QAction(QIcon.fromTheme('edit-paste', QIcon(icon_path+'edit-paste.png')), self.tr('Paste'), self)
		self.actionPaste.setShortcut(QKeySequence.Paste)
		self.connect(self.actionCut, SIGNAL('triggered()'), self.editBox, SLOT('cut()'))
		self.connect(self.actionCopy, SIGNAL('triggered()'), self.editBox, SLOT('copy()'))
		self.connect(self.actionPaste, SIGNAL('triggered()'), self.editBox, SLOT('paste()'))
		self.connect(qApp.clipboard(), SIGNAL('dataChanged()'), self.clipboardDataChanged)
		self.clipboardDataChanged()
		self.actionPlainText = QAction(self.tr('Plain text'), self)
		self.actionPlainText.setCheckable(True)
		self.connect(self.actionPlainText, SIGNAL('triggered(bool)'), self.enablePlainText)
		self.actionAutoFormatting = QAction(self.tr('Auto-formatting'), self)
		self.actionAutoFormatting.setCheckable(True)
		self.actionAutoFormatting.setChecked(True)
		self.actionRecentFiles = QAction(QIcon.fromTheme('document-open-recent', QIcon(icon_path+'document-open-recent.png')), self.tr('Open recent'), self)
		self.connect(self.actionRecentFiles, SIGNAL('triggered()'), self.openRecent)
		self.actionAbout = QAction(QIcon.fromTheme('help-about', QIcon(icon_path+'help-about.png')), self.tr('About %1').arg(app_name), self)
		self.actionAbout.setMenuRole(QAction.AboutRole)
		self.connect(self.actionAbout, SIGNAL('triggered()'), self.aboutDialog)
		self.actionAboutQt = QAction(self.tr('About Qt'), self)
		self.actionAboutQt.setMenuRole(QAction.AboutQtRole)
		if use_gdocs:
			self.actionsaveGDocs = QAction(QIcon.fromTheme('web-browser', QIcon(icon_path+'web-browser.png')), self.tr('Save to Google Docs'), self)
			self.connect(self.actionsaveGDocs, SIGNAL('triggered()'), self.saveGDocs)
		self.connect(self.actionAboutQt, SIGNAL('triggered()'), qApp, SLOT('aboutQt()'))
		self.usefulTags = ('a', 'center', 'i', 'img', 's', 'span', 'table', 'td', 'tr', 'u')
		self.usefulChars = ('hellip', 'laquo', 'minus', 'mdash', 'nbsp', 'ndash', 'raquo')
		self.tagsBox = QComboBox(self.editBar)
		self.tagsBox.addItem(self.tr('Tags'))
		self.tagsBox.addItems(self.usefulTags)
		self.connect(self.tagsBox, SIGNAL('activated(int)'), self.insertTag)
		self.symbolBox = QComboBox(self.editBar)
		self.symbolBox.addItem(self.tr('Symbols'))
		self.symbolBox.addItems(self.usefulChars)
		self.connect(self.symbolBox, SIGNAL('activated(int)'), self.insertSymbol)
		self.menubar = QMenuBar(self)
		self.menubar.setGeometry(QRect(0, 0, 800, 25))
		self.setMenuBar(self.menubar)
		self.menuFile = self.menubar.addMenu(self.tr('File'))
		self.menuEdit = self.menubar.addMenu(self.tr('Edit'))
		self.menuHelp = self.menubar.addMenu(self.tr('Help'))
		self.menuFile.addAction(self.actionNew)
		self.menuFile.addAction(self.actionOpen)
		self.menuFile.addAction(self.actionRecentFiles)
		self.menuFile.addSeparator()
		self.menuFile.addAction(self.actionSave)
		self.menuFile.addAction(self.actionSaveAs)
		self.menuFile.addSeparator()
		self.menuExport = self.menuFile.addMenu(self.tr('Export'))
		self.menuExport.addAction(self.actionPerfectHtml)
		self.menuExport.addAction(self.actionOdf)
		self.menuExport.addAction(self.actionPdf)
		if use_gdocs:
			self.menuExport.addSeparator()
			self.menuExport.addAction(self.actionsaveGDocs)
		self.menuFile.addAction(self.actionPrint)
		self.menuFile.addAction(self.actionPrintPreview)
		self.menuFile.addSeparator()
		self.menuFile.addAction(self.actionQuit)
		self.menuEdit.addAction(self.actionUndo)
		self.menuEdit.addAction(self.actionRedo)
		self.menuEdit.addSeparator()
		self.menuEdit.addAction(self.actionCut)
		self.menuEdit.addAction(self.actionCopy)
		self.menuEdit.addAction(self.actionPaste)
		self.menuEdit.addSeparator()
		self.menuEdit.addAction(self.actionPlainText)
		self.menuEdit.addAction(self.actionAutoFormatting)
		self.menuEdit.addSeparator()
		self.menuEdit.addAction(self.actionViewHtml)
		self.menuEdit.addAction(self.actionPreview)
		self.menuHelp.addAction(self.actionAbout)
		self.menuHelp.addAction(self.actionAboutQt)
		self.menubar.addMenu(self.menuFile)
		self.menubar.addMenu(self.menuEdit)
		self.menubar.addMenu(self.menuHelp)
		self.toolBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
		self.toolBar.addAction(self.actionOpen)
		self.toolBar.addAction(self.actionSave)
		self.toolBar.addAction(self.actionPrint)
		self.toolBar.addSeparator()
		self.toolBar.addAction(self.actionPreview)	
		self.editBar.addAction(self.actionUndo)
		self.editBar.addAction(self.actionRedo)
		self.editBar.addSeparator()
		self.editBar.addAction(self.actionCut)
		self.editBar.addAction(self.actionCopy)
		self.editBar.addAction(self.actionPaste)
		self.editBar.addWidget(self.tagsBox)
		self.editBar.addWidget(self.symbolBox)
		self.fileName = ""
	
	def preview(self, viewmode):
		self.editBar.setEnabled(not viewmode)
		self.editBox.setVisible(not viewmode)
		self.previewBox.setVisible(viewmode)
		if viewmode:
			if self.actionPlainText.isChecked():
				self.previewBox.setPlainText(self.editBox.toPlainText())
			else:
				self.previewBox.setHtml(self.parseText())
	
	def setCurrentFile(self):	
		self.setWindowTitle("")
		self.setWindowFilePath(self.fileName)
		settings = QSettings()
		files = settings.value("recentFileList").toStringList()
		files.prepend(self.fileName)
		files.removeDuplicates()
		if len(files) > 10:
			del files[10:]
		settings.setValue("recentFileList", files)
		QDir.setCurrent(QFileInfo(self.fileName).dir().path())
	
	def createNew(self):
		if self.maybeSave():
			self.fileName = ""
			self.editBox.clear()
			self.actionPreview.setChecked(False)
			self.actionPlainText.setChecked(False)
			self.enablePlainText(False)
			self.setWindowTitle(self.tr('New document') + '[*] ' + QChar(0x2014) + ' ' + app_name)
			self.setWindowFilePath("")
			self.editBox.document().setModified(False)
			self.modificationChanged(False)
			self.preview(False)
	
	def openRecent(self):
		settings = QSettings()
		filesOld = settings.value("recentFileList").toStringList()
		files = QStringList()
		for i in filesOld:
			if QFile.exists(i):
				files.append(i)
		settings.setValue("recentFileList", files)
		item, ok = QInputDialog.getItem(self, app_name, self.tr("Open recent"), files, 0, False)
		if ok and not item.isEmpty():
			self.fileName = item
			self.openFileMain()
    
	def openFile(self):
		if self.maybeSave():
			self.fileName = QFileDialog.getOpenFileName(self, self.tr("Open file"), "", \
			self.tr("ReText files (*.re *.md *.txt)")+";;"+self.tr("All files (*)"))
			self.openFileMain()
		
	def openFileMain(self):
		if QFile.exists(self.fileName):
			openfile = QFile(self.fileName)
			openfile.open(QIODevice.ReadOnly)
			openstream = QTextStream(openfile)
			html = openstream.readAll()
			openfile.close()
			self.actionPreview.setChecked(False)
			self.editBox.setPlainText(html)
			self.editBox.document().setModified(False)
			self.modificationChanged(False)
			self.preview(False)
			suffix = QFileInfo(self.fileName).suffix()
			if suffix.startsWith("htm"):
				self.actionAutoFormatting.setChecked(False)
			if not suffix == "txt":
				self.actionPlainText.setChecked(False)
				self.enablePlainText(False)
			self.setCurrentFile()
	
	def saveFile(self):
		self.saveFileMain(False)
	
	def saveFileAs(self):
		self.saveFileMain(True)
	
	def saveFileMain(self, dlg):
		if (not self.fileName) or dlg:
			if self.actionPlainText.isChecked() or self.actionAutoFormatting.isChecked():
				defaultExt = self.tr("ReText files (*.re *.md *.txt)")
			else:
				defaultExt = self.tr("HTML files (*.html *.htm)")
			self.fileName = QFileDialog.getSaveFileName(self, self.tr("Save file"), "", defaultExt)
		if self.fileName:
			if QFileInfo(self.fileName).suffix().isEmpty():
				self.fileName.append(".re")
			savefile = QFile(self.fileName)
			savefile.open(QIODevice.WriteOnly)
			savestream = QTextStream(savefile)
			savestream.__lshift__(self.editBox.toPlainText())
			savefile.close()
		self.editBox.document().setModified(False)	
		self.setCurrentFile()
		self.setWindowModified(False)
	
	def saveHtml(self, fileName):
		if QFileInfo(fileName).suffix().isEmpty():
			fileName.append(".html")
		if self.actionPlainText.isChecked():
			td = QTextDocument()
			td.setPlainText(self.editBox.toPlainText())
			writer = QTextDocumentWriter(fileName)
			writer.write(td)
		elif self.actionAutoFormatting.isChecked():
			htmlFile = QFile(fileName)
			htmlFile.open(QIODevice.WriteOnly)
			html = QTextStream(htmlFile)
			html.__lshift__("<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01 Transitional//EN\">\n")
			html.__lshift__("<html>\n<head>\n")
			html.__lshift__("  <meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\">\n")
			html.__lshift__(QString("  <meta name=\"generator\" content=\"%1 %2\">\n").arg(app_name, app_version))
			html.__lshift__("  <title>" + self.getDocumentTitle() + "</title>\n")
			html.__lshift__("</head>\n<body>\n")
			html.__lshift__(self.parseText())
			html.__lshift__("\n</body>\n</html>\n")
			htmlFile.close()
		else:
			td = QTextDocument()
			td.setHtml(self.editBox.toPlainText())
			writer = QTextDocumentWriter(fileName)
			writer.write(td)
	
	def textDocument(self):
		td = QTextDocument()
		if self.actionPlainText.isChecked():
			td.setPlainText(self.editBox.toPlainText())
		else:
			td.setHtml(self.parseText())
		return td
	
	def saveOdf(self):
		fileName = QFileDialog.getSaveFileName(self, self.tr("Export document to ODT"), "", self.tr("OpenDocument text files (*.odt)"))
		if QFileInfo(fileName).suffix().isEmpty():
			fileName.append(".odt")
		writer = QTextDocumentWriter(fileName)
		writer.setFormat("odf")
		writer.write(self.textDocument())
	
	def saveFilePerfect(self):
		fileName = None
		fileName = QFileDialog.getSaveFileName(self, self.tr("Save file"), "", self.tr("HTML files (*.html *.htm)"))
		if fileName:
			self.saveHtml(fileName)
	
	def savePdf(self):
		fileName = QFileDialog.getSaveFileName(self, self.tr("Export document to PDF"), "", self.tr("PDF files (*.pdf)"))
		if fileName:
			if QFileInfo(fileName).suffix().isEmpty():
				fileName.append(".pdf")
			printer = QPrinter(QPrinter.HighResolution)
			printer.setOutputFormat(QPrinter.PdfFormat)
			printer.setOutputFileName(fileName)
			printer.setDocName(self.getDocumentTitle())
			printer.setCreator(app_name+" "+app_version)
			self.textDocument().print_(printer)
	
	def printFile(self):
		printer = QPrinter(QPrinter.HighResolution)
		printer.setCreator(app_name+" "+app_version)
		dlg = QPrintDialog(printer, self)
		dlg.setWindowTitle(self.tr("Print document"))
		if (dlg.exec_() == QDialog.Accepted):
			self.textDocument().print_(printer)
	
	def printFileMain(self, printer):
		self.textDocument().print_(printer)
	
	def printPreview(self):
		printer = QPrinter(QPrinter.HighResolution)
		printer.setCreator(app_name+" "+app_version)
		preview = QPrintPreviewDialog(printer, self)
		self.connect(preview, SIGNAL("paintRequested(QPrinter*)"), self.printFileMain)
		preview.exec_()
	
	def getDocumentTitle(self):
		if self.fileName:
			return QFileInfo(self.fileName).completeBaseName()
		else:
			return self.tr("New document")
	
	def saveGDocs(self):
		settings = QSettings()
		login = settings.value("GDocsLogin").toString()
		passwd = settings.value("GDocsPasswd").toString()
		loginDialog = LogPassDialog(login, passwd)
		if loginDialog.exec_() == QDialog.Accepted:
			login = loginDialog.loginEdit.text()
			passwd = loginDialog.passEdit.text()
			self.saveHtml('temp.html')
			gdClient = gdata.docs.service.DocsService(source=app_name)
			try:
				gdClient.ClientLogin(unicode(login), unicode(passwd))
			except gdata.service.BadAuthentication:
				QMessageBox.warning (self, app_name, self.tr("Incorrect user name or password!"))
			else:
				settings.setValue("GDocsLogin", login)
				settings.setValue("GDocsPasswd", passwd)
				ms = MediaSource(file_path='temp.html', content_type='text/html')
				entry = gdClient.Upload(ms, unicode(self.getDocumentTitle()))
				link = entry.GetAlternateLink().href
				QFile('temp.html').remove()
				QDesktopServices.openUrl(QUrl(link))
	
	def modificationChanged(self, changed):
		self.actionSave.setEnabled(changed)
		self.setWindowModified(changed)
	
	def clipboardDataChanged(self):
		self.actionPaste.setEnabled(qApp.clipboard().mimeData().hasText())
	
	def insertTag(self, num):
		if num:
			ut = self.usefulTags[num-1]
			hc = not ut in ('img', 'td', 'tr')
			arg = ''
			if ut == 'a':
				arg = ' href=""'
			if ut == 'img':
				arg = ' src=""'
			if ut == 'span':
				arg = ' style=""'
			tc = self.editBox.textCursor()
			if hc:
				toinsert = '<'+ut+arg+'>'+tc.selectedText()+'</'+ut+'>'
				tc.removeSelectedText
				tc.insertText(toinsert)
			else:
				tc.insertText('<'+ut+arg+'>'+tc.selectedText())
		self.tagsBox.setCurrentIndex(0)
	
	def insertSymbol(self, num):
		if num:
			self.editBox.insertPlainText('&'+self.usefulChars[num-1]+';')
		self.symbolBox.setCurrentIndex(0)
	
	def maybeSave(self):
		if not self.editBox.document().isModified():
			return True
		ret = QMessageBox.warning(self, app_name, self.tr("The document has been modified.\nDo you want to save your changes?"), \
		QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
		if ret == QMessageBox.Save:
			self.saveFileMain(False)
			return True
		elif ret == QMessageBox.Cancel:
			return False
		return True
	
	def closeEvent(self, closeevent):
		if self.maybeSave():
			closeevent.accept()
		else:
			closeevent.ignore()
	
	def viewHtml(self):
		HtmlDlg = HtmlDialog(self)
		HtmlDlg.setWindowTitle(self.getDocumentTitle()+" ("+self.tr("HTML code")+") "+QChar(0x2014)+" "+app_name)
		HtmlDlg.textEdit.setPlainText(self.parseText())
		HtmlDlg.show()
		HtmlDlg.raise_()
		HtmlDlg.activateWindow()
		
	def aboutDialog(self):
		QMessageBox.about(self, self.tr('About %1').arg(app_name), '<p>' \
		+ self.tr('This is <b>%1</b>, version %2<br>Author: Dmitry Shachnev, 2011').arg(app_name, app_version) \
		+ '</p><p>'+ self.tr('Website: <a href="http://sourceforge.net/p/retext/">sf.net/p/retext</a>') + '<br>' \
		+ self.tr('MarkDown syntax documentation: <a href="http://daringfireball.net/projects/markdown/syntax">daringfireball.net/projects/markdown/syntax</a>') + '</p>')
	
	def enablePlainText(self, value):
		self.actionAutoFormatting.setDisabled(value)
		self.actionPerfectHtml.setDisabled(value)
		self.actionViewHtml.setDisabled(value)
		self.tagsBox.setVisible(value)
		self.symbolBox.setVisible(value)
	
	def parseText(self):
		htmltext = self.editBox.toPlainText()
		if self.actionAutoFormatting.isChecked():
			toinsert = md.convert(unicode(htmltext))
		else:
			toinsert = htmltext
		return toinsert

def main(fileName):
	app = QApplication(sys.argv)
	app.setOrganizationName("ReText project")
	app.setApplicationName("ReText")
	RtTranslator = QTranslator()
	if not RtTranslator.load("retext_"+QLocale.system().name()):
		if sys.platform == "linux2":
			RtTranslator.load("retext_"+QLocale.system().name(), "/usr/lib/retext")
	QtTranslator = QTranslator()
	QtTranslator.load("qt_"+QLocale.system().name(), QLibraryInfo.location(QLibraryInfo.TranslationsPath))
	app.installTranslator(RtTranslator)
	app.installTranslator(QtTranslator)
	window = ReTextWindow()
	if QFile.exists(QString.fromUtf8(fileName)):
		window.fileName = QString.fromUtf8(fileName)
		window.openFileMain()
	window.show()
	sys.exit(app.exec_())

if __name__ == '__main__':
	if len(sys.argv) > 1:
		main(sys.argv[1])
	else:
		main("")
