<%inherit file="/base.mako"/>

<h2>Tags</h2>
${self.listTags()}

<h2>Group Expenditures</h2>
${self.listExpenditures(c.expenditures)}

<h2>Transfers</h2>
${self.listTransfers(c.transfers)}
