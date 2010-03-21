<%inherit file="/base.mako"/>

<h2>Tags</h2>
${self.listTags()}

<h2>Expenditures tagged with ${c.tag.name}</h2>
${self.listExpenditures(c.expenditures, total=c.total, share=c.share)}
