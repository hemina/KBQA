#coding=utf8
import sys
sys.path.insert(0, '..')
from flask import Flask
from flask.ext.bootstrap import Bootstrap
from flask import render_template,request
from flask_thriftclient import ThriftClient
from kb_manager.gen_py.freebase_service import FreebaseService
from utils.db_manager import DBManager
# from kb_manager.es_freebase import FreebaseHelper
# from kb_manager.freebase_client import FreebaseClient
from tagger.predict import EntityMentionTagger, EntityLinker
import json
import globals

static_path = 'static'


class KBQADemo(object):
    def __init__(self, dir_path):
        self.app = Flask(__name__, template_folder=static_path, static_folder=static_path)
        self.app.config["THRIFTCLIENT_SSL_VALIDATE"] = False
        self.app.config["THRIFTCLIENT_TRANSPORT"] = "https://127.0.0.1:8888"
        self.bootstrap = Bootstrap(self.app)
        self.tagger = EntityMentionTagger(dir_path)
        # self.freebase_helper = FreebaseHelper()
        self.freebase = ThriftClient(FreebaseService.Client, self.app)
        self.entity_linker = EntityLinker(self.tagger)
        @self.app.route("/kbqa")
        def main():
            return render_template('main.html', params={})

        @self.app.route('/get_entity_mention', methods=['GET', 'POST'])
        def get_entity_mention():
            print "[get_entity_mention]"
            sentence = request.args.get('sentence')
            print sentence
            res = self.tagger.tag(sentence)
            res['mentions'] = '<br>'.join(['(%s, %s)' % (m, s) for m, s in res['mentions'].items()])
            return json.dumps(res)

        @self.app.route('/link_entity', methods=['GET', 'POS'])
        def link_entity():
            sentence = request.args.get('sentence')
            print '[link entity]', sentence
            sentence, candidates = self.entity_linker.get_candidate_topic_entities(sentence)
            res = []
            for mid, feat in candidates.items():
                res.append('{}: ({}, {}, {})'.format(mid, feat['mention'], feat['entity_score'], feat['mention_score']))
            return json.dumps({'candidates': '<br>'.join(res)})

        @self.app.route('/mid_to_name', methods=['GET', 'POST'])
        def get_name_by_mid():
            mid = request.args.get('mid').strip()
            print "[get_name_by_mid]", mid

            name, name_info = DBManager.get_name(mid)
            print name, name_info
            aliases, alias_info = DBManager.get_alias(mid)
            res = {'name': name if name else name_info,
                   'alias': '<br>'.join(aliases) if aliases else alias_info}
            return json.dumps(res)

        @self.app.route('/surface_to_mids', methods=['GET', 'POST'])
        def get_mids_by_surface():
            surface = request.args.get('surface').strip()
            print '[get_mid_by_surface]'

            mids = DBManager.get_candidate_entities(surface, 0.1)
            print mids
            res = {'candidates': '<br>'.join('%s %s' % (m[0], m[1]) for m in mids)}
            return json.dumps(res)

        @self.app.route('/get_subgraph', methods=['GET', 'POST'])
        def get_subgraph():
            mid = request.args.get('mid').strip()
            print '[get_subgraph]', mid
            subgraph = self.freebase.client.get_subgraph(mid)
            print "subgraph", subgraph
            links = []
            nodes_ = {}

            for path in subgraph:
                if len(path) == 1:
                    p1 = path[0]
                    if p1[0] not in nodes_:
                        nodes_[p1[0]] = {'category': 0, 'name': p1[0], 'value': 10}

                    if p1[2] not in nodes_:
                        nodes_[p1[2]] = {'category': 2, 'name': p1[2], 'value': 4}
                else:
                    p1 = path[0]
                    if p1[0] not in nodes_:
                        nodes_[p1[0]] = {'category': 0, 'name': p1[0], 'value': 10}
                    if p1[2] not in nodes_:
                        nodes_[p1[2]] = {'category': 1, 'name': p1[2], 'value': 4}
                    p2 = path[1]
                    if p2[2] not in nodes_:
                        nodes_[p2[2]] = {'category': 2, 'name': p2[2], 'value': 4}

            for m in nodes_.keys():
                name, name_info = DBManager.get_name(m)
                nodes_[m]['label'] = name

            nodes = nodes_.values()

            for path in subgraph:
                if len(path) == 1:
                    t = path[0]
                    links.append(
                        {'source': nodes_[t[0]]['name'], 'target': nodes_[t[2]]['name'], 'weight': 2, 'name': t[1]})
                else:
                    t = path[0]
                    links.append(
                        {'source': nodes_[t[0]]['name'], 'target': nodes_[t[2]]['name'], 'weight': 2, 'name': t[1]})
                    t = path[1]
                    links.append(
                        {'source': nodes_[t[0]]['name'], 'target': nodes_[t[2]]['name'], 'weight': 2, 'name': t[1]})
            print 'node', nodes
            print 'links', links

            return json.dumps({'nodes': nodes, 'links': links})

        # @self.app.route('/get_subgraph', methods=['GET', 'POST'])
        # def get_subgraph():
        #     mid = request.args.get('mid').strip()
        #     print '[get_subgraph]', mid
        #     subgraph = self.freebase.get_subgraph(mid)
        #     subgraph = self.freebase_helper.get_subgraph(mid)
        #     print subgraph
        #     links = []
        #     nodes_ = {}
        #
        #     for t in subgraph:
        #         if t[0] not in nodes_:
        #             nodes_[t[0]] = {'category': 1, 'name': t[0], 'value': 1}
        #         if t[0] == mid:
        #             nodes_[t[0]]['category'] = 0
        #             nodes_[t[0]]['value'] = 10
        #         if t[2] not in nodes_:
        #             nodes_[t[2]] = {'category': 1, 'name': t[2], 'value': 4}
        #             if t[3] == 0 or t[3] == 2:
        #                 nodes_[t[2]]['category'] = 2
        #
        #     for m in nodes_.keys():
        #         name, name_info = DBManager.get_name(m)
        #         nodes_[m]['label'] = name
        #
        #     nodes = nodes_.values()
        #     for t in subgraph:
        #         links.append({'source': nodes_[t[0]]['name'], 'target': nodes_[t[2]]['name'], 'weight': 2, 'name': t[1]})
        #     print 'node', nodes
        #     print 'links', links
        #
        #     return json.dumps({'nodes':nodes, 'links':links})

    def run(self, port, debug=False):
        self.app.run(host='0.0.0.0',port=port, debug=debug)

if __name__ == '__main__':
    globals.read_configuration('../config.cfg')
    obj = KBQADemo(sys.argv[1])
    obj.run(7778, True)
