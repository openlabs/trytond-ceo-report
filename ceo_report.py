# -*- coding: utf-8 -*-
"""
    ceo_report.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from openlabs_report_webkit import ReportWebkit

from trytond.pool import Pool
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateAction, StateView, Button
from trytond.transaction import Transaction

__all__ = ['CEOReport', 'GenerateCEOReport', 'GenerateCEOReportStart']


class CEOReport(ReportWebkit):
    __name__ = 'ceo.report'

    @classmethod
    def wkhtml_to_pdf(cls, data, options=None):
        """
        Call wkhtmltopdf to convert the html to pdf
        """
        Company = Pool().get('company.company')

        company = ''
        if Transaction().context.get('company'):
            company = Company(Transaction().context.get('company')).party.name
        options = {
            'margin-bottom': '0.50in',
            'margin-left': '0.50in',
            'margin-right': '0.50in',
            'margin-top': '0.50in',
            'footer-font-size': '8',
            'footer-left': company,
            'footer-line': '',
            'footer-right': '[page]/[toPage]',
            'footer-spacing': '5',
        }
        return super(CEOReport, cls).wkhtml_to_pdf(
            data, options=options
        )

    @classmethod
    def parse(cls, report, records, data, localcontext):
        Sale = Pool().get('sale.sale')
        ShipmentOut = Pool().get('stock.shipment.out')
        Inventory = Pool().get('stock.inventory')
        Production = Pool().get('production')

        days = 1

        # Can be used for generating report for multiple days
        if data.get('days'):
            days = data['days']

        sales = Sale.search([
            ('state', 'in', ['confirmed', 'processing', 'done']),
            ('write_date', '>=', (datetime.today() - relativedelta(days=days))),
        ])
        shipments = ShipmentOut.search([
            ('state', 'in', ['done', 'packed', 'assigned', 'waiting']),
            ('write_date', '>=', (datetime.today() - relativedelta(days=days))),
        ])
        productions = Production.search([
            ('state', 'in', ['done', 'running', 'assigned', 'waiting']),
            ('write_date', '>=', (datetime.today() - relativedelta(days=days))),
        ])
        inventories = Inventory.search([
            ('date', '>=', (date.today() - relativedelta(days=days))),
        ])
        done_shipments_today = ShipmentOut.search([
            ('effective_date', '>=', (date.today() - relativedelta(days=days))),
            ('state', '=', 'done'),
        ], count=True)

        localcontext.update({
            'sales': sales,
            'shipments': shipments,
            'productions': productions,
            'inventories': inventories,
            'done_shipments_today': done_shipments_today,
        })
        return super(CEOReport, cls).parse(
            report, records, data, localcontext
        )


class GenerateCEOReportStart(ModelView):
    'Generate CEO Report'
    __name__ = 'ceo.report.generate.start'

    days = fields.Integer('No. of Days')


class GenerateCEOReport(Wizard):
    'Generate CEO Report Wizard'
    __name__ = 'ceo.report.generate'

    start = StateView(
        'ceo.report.generate.start',
        'ceo_report.ceo_report_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'generate', 'tryton-ok', default=True),
        ]
    )
    generate = StateAction('ceo_report.ceo_report')

    def do_generate(self, action):
        """
        Sends the selected shop and customer as report data
        """
        data = {
            'days': self.start.days or 1,
        }
        return action, data

    def transition_generate(self):
        return 'end'
