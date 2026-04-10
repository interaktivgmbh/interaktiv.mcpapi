from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.component import getAdapters

from interaktiv.mcpapi.interfaces import IMCPTool


class MCPAPISettingsView(BrowserView):
    template = ViewPageTemplateFile('templates/settings.pt')

    def __call__(self):
        return self.template(self)

    def get_tools(self):
        tools = []
        for name, tool in getAdapters((self.context, self.request), IMCPTool):
            module = tool.__class__.__module__
            package = '.'.join(module.split('.')[:2])
            tools.append({
                'name': tool.name,
                'description': tool.description,
                'permission': tool.permission,
                'schema': tool.schema,
                'package': package,
            })
        return sorted(tools, key=lambda t: t['name'])
