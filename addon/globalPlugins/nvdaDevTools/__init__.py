#__init__.py
# Copyright (C) 2016 Babbage Automation
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.

import gui
import wx
import api
import scriptHandler
import globalPluginHandler
import ui
import config
import globalVars
import addonHandler
import controlTypes
from logHandler import log
import collections

_addonDir = os.path.join(os.path.dirname(__file__), "..", "..").decode("mbcs")
_curAddon = addonHandler.Addon(_addonDir)
_addonSummary = _curAddon.manifest['summary']
_scriptCategory = unicode(_addonSummary)
addonHandler.initTranslation()

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = _scriptCategory

	toolsMenu = gui.mainFrame.sysTrayIcon.toolsMenu

	def __init__(self, *args, **kwargs):
		super(GlobalPlugin, self).__init__(*args, **kwargs)
		self.createMenu()

	def onObjectTreeCommand(self,evt):
		if gui.isInMessageBox:
			return
		gui.MainFrame.prePopup(gui.mainFrame)
		d=ObjectTreeDialog(gui.mainFrame, wx.ID_ANY, _("NVDA objects overview"))
		d.Show()
		gui.MainFrame.postPopup(gui.mainFrame)

	def createMenu(self):
		self.objectTreeMenuItem = self.toolsMenu.Append(wx.ID_ANY, _("Object Tree"), _(""))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onObjectTreeCommand, self.objectTreeMenuItem)

	def script_showObjectTree(self, gesture):
		wx.CallAfter(self.onObjectTreeCommand, None)
	# Translators: the description for the object tree script.
	script_showObjectTree.__doc__ = _("Presents a tree containing all NVDA objects, i.e. objects which can be navigate to using object navigation")

	def terminate(self):
		self.toolsMenu.RemoveItem(self.objectTreeMenuItem)
		self.objectTreeMenuItem.Destroy()
		self.objectTreeMenuItem=None
		# We want to re-enable config profile triggers when they were disabled by us

class ObjectTreeDialog(wx.Dialog):
	includeInvisibleObjects = True
	_objects = []
	Object = collections.namedtuple("Object", ("obj", "label", "parent"))

	def __init__(self,*args, **kwargs):
		super(ObjectTreeDialog, self).__init__(*args, **kwargs)
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		# Translators: The label of the tree view containing objects
		# in the object tray dialog.
		label = wx.StaticText(self, wx.ID_ANY, _("&Objects"))
		mainSizer.Add(label)
		self.tree = wx.TreeCtrl(self, wx.ID_ANY, style=wx.TR_HAS_BUTTONS | wx.TR_HIDE_ROOT | wx.TR_SINGLE | wx.TR_EDIT_LABELS)
		self.tree.Bind(wx.EVT_SET_FOCUS, self.onTreeSetFocus)
		self.treeRoot = self.tree.AddRoot("root")
		mainSizer.Add(self.tree,proportion=7,flag=wx.EXPAND)

		sizer = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: The label of an editable text field to filter the objects
		# in the object tray dialog.
		label = wx.StaticText(self, wx.ID_ANY, _("&Filter by:"))
		sizer.Add(label)
		self.filterEdit = wx.TextCtrl(self, wx.ID_ANY)
		self.filterEdit.Bind(wx.EVT_TEXT, self.onFilterEditTextChange)
		sizer.Add(self.filterEdit)
		mainSizer.Add(sizer,proportion=1)

		sizer = wx.BoxSizer(wx.HORIZONTAL)
		sizer.Add(wx.Button(self, wx.ID_CANCEL))
		mainSizer.Add(sizer,proportion=1)

		mainSizer.Fit(self)
		self.SetSizer(mainSizer)
		self.postInit()

	def postInit(self):
		# This shouldn't happen to often, as it wil freeze NVDA when there are many objects
		self.generateObjectsList(api.getDesktopObject())
		self.tree.SetFocus()
		self.populateTree()
		self.Center(wx.BOTH | wx.CENTER_ON_SCREEN)

	def populateTree(self):
		self.tree.DeleteChildren(self.treeRoot)
		objectsToTreeItems = {}
		for objectTuple in self._objects:
			parent = objectsToTreeItems.get(objectTuple.parent)
			item = self.tree.AppendItem(parent or self.treeRoot, objectTuple.label)
			self.tree.SetItemPyData(item, objectTuple)
			objectsToTreeItems[objectTuple] = item
		self.tree.ExpandAll()

	def generateObjectsList(self, root):
		if config.conf.profileTriggersEnabled:
			config.conf.profileTriggersEnabled=False
			
		self._objects=[]
		parents = []
		# We can simply start from the root, find every recursive escendant and throw it in a list
		for obj in root.recursiveDescendants:
			label=", ".join([obj.name or _("unlabeled"), controlTypes.roleLabels[obj.role], obj.windowClassName])		
			for parent in reversed(parents):
				if obj in parent.obj.children:
					break
				else:
					# We're not a child of this parent, so this parent has no more children and can be removed from the stack.
					parents.pop()
			else:
				# No parent found, so we're at the root.
				# Note that parents will be empty at this point, as all parents are no longer relevant and have thus been removed from the stack.
				parent = None
			object=self.Object(obj,label,parent)
			self._objects.append(object)
			# This could be the parent of a subsequent element, so add it to the parents stack.
			parents.append(object)

	def onTreeSetFocus(self, evt):
		evt.Skip()

	def onFilterEditTextChange(self, evt):
		#self.filter(self.filterEdit.GetValue())
		evt.Skip()
