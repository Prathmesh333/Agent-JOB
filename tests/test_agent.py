import csv, tempfile, unittest
from datetime import date,timedelta
from pathlib import Path
from recruiter_outreach.agent import connect,canonical,import_leads,draft,transition,due

class AgentTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.db=connect(Path(self.tmp.name)/'db.sqlite');self.addCleanup(self.db.close)
  self.csv=Path(self.tmp.name)/'leads.csv'
  with self.csv.open('w',newline='') as f:
   w=csv.writer(f);w.writerow(['name','company','title','profile_url','role','evidence'])
   w.writerow(['Alex Smith','Acme','Technical Recruiter','https://www.linkedin.com/in/alex-smith/?trk=x','AI Engineer','AI careers page'])
 def test_domain_validation(self):
  self.assertEqual(canonical('https://www.linkedin.com/in/alex-smith/?trk=x'),'https://www.linkedin.com/in/alex-smith')
  with self.assertRaises(ValueError):canonical('https://linkedin.com.evil/in/x')
 def test_dedup(self):
  self.assertEqual(import_leads(self.db,self.csv)['added'],1)
  self.assertEqual(import_leads(self.db,self.csv)['duplicate'],1)
 def test_gate_and_reply(self):
  import_leads(self.db,self.csv)
  with self.assertRaises(ValueError):transition(self.db,1,'sent')
  message=draft(self.db,1,{'name':'Sam','intro':'I am an ML graduate.','proof':'I built a real ML project.'})
  self.assertIn('Acme',message)
  transition(self.db,1,'approve');transition(self.db,1,'sent');transition(self.db,1,'replied')
  self.assertEqual(due(self.db,0),[])
 def test_max_two_followups(self):
  import_leads(self.db,self.csv);draft(self.db,1,{'name':'Sam','intro':'Graduate','proof':'Built a project'})
  transition(self.db,1,'approve');transition(self.db,1,'sent')
  for _ in range(2):
   old=(date.today()-timedelta(days=10)).isoformat()
   self.db.execute('UPDATE leads SET last_contact=? WHERE id=1',(old,));self.db.commit()
   self.assertEqual(len(due(self.db)),1);transition(self.db,1,'followup')
  self.assertEqual(due(self.db,0),[])
  with self.assertRaises(ValueError):transition(self.db,1,'followup')
if __name__=='__main__':unittest.main()
