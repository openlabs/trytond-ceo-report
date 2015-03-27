# -*- coding: utf-8 -*-
"""
    ceo_report.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import json
from datetime import datetime, time, date
from dateutil.relativedelta import relativedelta
from openlabs_report_webkit import ReportWebkit
from itertools import groupby

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
            'javascript-delay': '100',
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

        sales = Sale.search([
            ('state', 'in', ['confirmed', 'processing', 'done']),
            ('sale_date', '>=', data['start_date'].date()),
            ('sale_date', '<=', data['end_date'].date()),
        ])
        shipments = ShipmentOut.search([
            ('state', 'in', ['done', 'packed', 'assigned', 'waiting']),
            ('write_date', '>=', data['start_date']),
            ('write_date', '<=', data['end_date']),
        ])
        productions = Production.search([
            ('state', 'in', ['done', 'running', 'assigned', 'waiting']),
            ('write_date', '>=', data['start_date']),
            ('write_date', '<=', data['end_date']),
        ])
        inventories = Inventory.search([
            ('date', '>=', data['start_date'].date()),
            ('date', '<=', data['end_date'].date()),
        ])
        done_shipments_today = ShipmentOut.search([
            ('effective_date', '>=', data.get('start_date').date()),
            ('effective_date', '<=', data.get('end_date').date()),
            ('state', '=', 'done'),
        ], count=True)

        localcontext.update({
            'sales': sales,
            'shipments': shipments,
            'productions': productions,
            'inventories': inventories,
            'done_shipments_today': done_shipments_today,
            'sale_has_salesman': hasattr(Sale, 'employee'),
            'sale_has_channel': hasattr(Sale, 'channel'),
            'get_sales_by_salesman_data': cls.get_sales_by_salesman_data,
            'get_sales_by_channel_data': cls.get_sales_by_channel_data
        })
        return super(CEOReport, cls).parse(
            report, records, data, localcontext
        )

    @classmethod
    def get_sales_by_salesman_data(cls, sales):
        """
        Extracts the data from sales and returns it in the form
        understandable for the graph
        """
        sales_by_salesman = []

        for salesman, records in groupby(
            sorted(sales, key=lambda s: s.employee),
            key=lambda s: s.employee
        ):
            sales_by_salesman.append([
                salesman and salesman.party.name or "(not set)",
                len(list(records))
            ])

        return json.dumps(sales_by_salesman)

    @classmethod
    def get_sales_by_channel_data(cls, sales):
        """
        Extracts the data from sales and returns it in the form
        understandable for the graph
        """
        sales_by_channel = []

        for channel, records in groupby(
            sorted(sales, key=lambda s: s.channel),
            key=lambda s: s.channel
        ):
            sales_by_channel.append([
                channel and channel.name or "Others",
                len(list(records))
            ])

        return json.dumps(sales_by_channel)


class GenerateCEOReportStart(ModelView):
    'Generate CEO Report'
    __name__ = 'ceo.report.generate.start'

    start_date = fields.DateTime('Start Date', required=True)
    end_date = fields.DateTime('End Date', required=True)

    @staticmethod
    def default_start_date():
        return datetime.combine(
            date.today() - relativedelta(days=1),
            time.min
        )

    @staticmethod
    def default_end_date():
        return datetime.combine(
            date.today() - relativedelta(days=1),
            time.max
        )


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
        Sends the date range as report data
        """
        data = {
            'start_date': self.start.start_date,
            'end_date': self.start.end_date,
        }
        return action, data

    def transition_generate(self):
        return 'end'
