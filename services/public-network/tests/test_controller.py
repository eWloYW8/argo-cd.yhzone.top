import copy
import importlib.util
from pathlib import Path
import unittest
s = importlib.util.spec_from_file_location('controller', Path(__file__).parents[1] / 'controller/controller.py')
c = importlib.util.module_from_spec(s); s.loader.exec_module(c)
READY = {'conditions': [{'type':'Ready','status':'True'}]}
class Reconciliation(unittest.TestCase):
    def setUp(self):
        self.nodes = {n:{'status':copy.deepcopy(READY)} for n in ['ali-sas','worker']}
        self.resources = [{'metadata':{'name':'worker'},'spec':{'address':'2001:4860::1'}}]
        self.svc = [{'metadata':{'namespace':'test','name':'app','annotations':{'traefik.ingress.kubernetes.io/service.nativelb':'true'}},'spec':{'trafficDistribution':'PreferSameNode'}}]
        self.slices = [{'metadata':{'namespace':'test','labels':{'kubernetes.io/service-name':'app'}},'endpoints':[{'nodeName':'worker','conditions':{'ready':True}}]}]
        self.ing = [{'metadata':{'name':'app','namespace':'test','labels':{c.GROUP+'/exposure':'public'}},'spec':{'ingressClassName':'traefik-public','tls':[{'hosts':['app.yhzone.top'],'secretName':'tls'}],'rules':[{'host':'app.yhzone.top','http':{'paths':[{'backend':{'service':{'name':'app'}}}]}}]}}]
        self.certs = [{'metadata':{'namespace':'test'},'spec':{'secretName':'tls','dnsNames':['app.yhzone.top']},'status':copy.deepcopy(READY)}]
    def records(self, resources=None, gateways=None):
        a=c.authorized_addresses(self.resources if resources is None else resources,self.nodes)
        return c.calculate(self.ing,self.svc,self.slices,self.nodes,a,{'ali-sas','worker'} if gateways is None else gateways,self.certs)[0].get('app.yhzone.top',[])
    def test_explicit_ipv6_only(self):
        self.assertEqual([x['recordType'] for x in self.records()],['A','AAAA'])
        self.assertEqual([x['recordType'] for x in self.records(resources=[])],['A'])
    def test_disabled_invalid_or_absent_node(self):
        for addr in ['fd00::1','fe80::1','2001:db8::1','1.2.3.4','bad']:
            self.resources[0]['spec']['address']=addr
            self.assertEqual([x['recordType'] for x in self.records()],['A'])
        self.resources[0]['spec']={'address':'2001:4860::1','enabled':False}
        self.assertEqual([x['recordType'] for x in self.records()],['A'])
    def test_ready_backend_and_gateway_required(self):
        self.assertEqual([x['recordType'] for x in self.records(gateways={'ali-sas'})],['A'])
        self.slices[0]['endpoints'][0]['conditions']['ready']=False
        self.assertEqual([x['recordType'] for x in self.records()],['A'])
    def test_node_move_withdraws_ipv6(self):
        self.slices[0]['endpoints'][0]['nodeName']='ali-sas'
        self.assertEqual([x['recordType'] for x in self.records()],['A'])
    def test_local_routing_required(self):
        self.svc[0]['spec'].clear()
        self.assertEqual([x['recordType'] for x in self.records()],['A'])
    def test_private_or_unissued_domains_not_published(self):
        self.ing[0]['spec']['rules'][0]['host']='app.k8s.yhzone.top'
        self.assertEqual(self.records(),[])
        self.ing[0]['spec']['rules'][0]['host']='app.yhzone.top';self.certs=[]
        self.assertEqual(self.records(),[])
    def test_missing_backend_and_duplicate_host(self):
        self.svc=[];self.assertEqual(self.records(),[])
        self.setUp();self.ing.append(copy.deepcopy(self.ing[0]));self.assertEqual(self.records(),[])
    def test_legacy_uses_easytier_without_frp(self):
        text=c.haproxy_config(['app.yhzone.top'])
        self.assertIn('server legacy 10.1.2.4:21443',text)
        self.assertNotIn('server legacy 127.0.0.1:21443',text)
        self.assertIn('server local 127.0.0.1:20444 send-proxy-v2',text)
    def test_sni_private_block_precedes_legacy(self):
        text=c.haproxy_config(['app.yhzone.top'])
        self.assertLess(text.index('content reject'),text.index('default_backend legacy'))
if __name__=='__main__':unittest.main()
