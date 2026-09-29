import csv, os, tempfile, unittest
from search_validator.engine.dedup import write_deduplicated_outputs
from search_validator.engine.schema import ROW_FIELDS, Config
from search_validator.engine.anchors import check_anchors

class CoreTests(unittest.TestCase):
    def setUp(self): self.d=tempfile.mkdtemp()
    def _write_results(self, filename, rows):
        p=os.path.join(self.d,filename)
        with open(p,'w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=ROW_FIELDS); w.writeheader(); w.writerows(rows)
        return p
    def _row(self, db, rid, doi, title, authors, year, q='Q1'):
        r={k:'' for k in ROW_FIELDS}; r.update(query_id=q,family='F',substream='S',database=db,id=rid,doi=doi,title=title,authors=authors,year=year); return r
    def _log(self, entries):
        fields=['run_id','query_id','database','translation_version','translation_status','date_run','translated_query','total_hits_reported','records_retrieved','retrieval_truncated','export_filename','status','error_message']
        with open(os.path.join(self.d,'search_log.csv'),'w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(entries)
    def test_dedup_doi_and_provenance(self):
        a=self._write_results('a.csv',[self._row('OpenAlex','a','10.1/X','Same paper','Jane Smith',2020)])
        b=self._write_results('b.csv',[self._row('PubMed','b','https://doi.org/10.1/x','Same paper','Smith, Jane',2020)])
        self._log([dict(run_id='1',query_id='Q1',database='OpenAlex',export_filename=a,status='OK'),dict(run_id='1',query_id='Q1',database='PubMed',export_filename=b,status='OK')])
        c,p,r=write_deduplicated_outputs(self.d)
        self.assertEqual(len(c),1); self.assertEqual(len(p),2); self.assertEqual(len(r),0)
    def test_conflicting_dois_not_merged(self):
        a=self._write_results('a.csv',[self._row('OpenAlex','a','10.1/a','Same paper','Jane Smith',2020)])
        b=self._write_results('b.csv',[self._row('PubMed','b','10.1/b','Same paper','Smith, Jane',2020)])
        self._log([dict(run_id='1',query_id='Q1',database='OpenAlex',export_filename=a,status='OK'),dict(run_id='1',query_id='Q1',database='PubMed',export_filename=b,status='OK')])
        c,p,r=write_deduplicated_outputs(self.d)
        self.assertEqual(len(c),2); self.assertEqual(len(r),1)
    def test_anchor_surname_from_display_name(self):
        a=self._write_results('a.csv',[self._row('OpenAlex','a','','Canonical Title','Jane Smith',2020)])
        self._log([dict(run_id='1',query_id='Q1',database='OpenAlex',export_filename=a,status='OK')])
        bench=os.path.join(self.d,'bench.csv')
        with open(bench,'w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=['record_id','first_author','year','title','doi_or_url','indexed_in_openalex? (Y/N)']); w.writeheader(); w.writerow(dict(record_id='B1',first_author='Smith',year='2020',title='Canonical Title',doi_or_url='',**{'indexed_in_openalex? (Y/N)':'Y'}))
        q={'Q1':{'anchors':['Smith'],'anchor_ids':[],'routes':['openalex'],'family':'F','substream':'S','text':'x'}}
        rows=check_anchors(q,bench,self.d,Config(),verbose=False)
        self.assertTrue(rows[0]['classification'].startswith('RECOVERED'))

if __name__=='__main__': unittest.main()
