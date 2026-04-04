from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class CustomerPortalFinance(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)

        partner = request.env.user.partner_id

        if 'finance_count' in counters:
            finance_count = request.env['cc.finance'].sudo().search_count([
                ('partner_id', '=', partner.id),
                ('state', '=', 'confirmed')
            ])
            values['finance_count'] = finance_count

        return values

    @http.route(['/my/finance', '/my/finance/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_finance(self, page=1, **kw):

        partner = request.env.user.partner_id
        Finance = request.env['cc.finance'].sudo()

        domain = [
            ('partner_id', '=', partner.id),
            ('state', '=', 'confirmed')
        ]

        total = Finance.search_count(domain)

        pager = portal_pager(
            url="/my/finance",
            total=total,
            page=page,
            step=20
        )

        records = Finance.search(
            domain,
            order="date desc, id desc",
            limit=20,
            offset=pager['offset']
        )

        values = {
            "records": records,
            "page_name": "finance",
            "pager": pager,
            "default_url": "/my/finance",
        }

        return request.render("edu_finance.portal_my_finance", values)
