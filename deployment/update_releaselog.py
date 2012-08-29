#!/usr/bin/python

import atom.data
import gdata.sites.client
import gdata.sites.data
import time
import os
import commands
from xml.sax.saxutils import escape
import conf

class SitesUpdater:
  """ Updates HashCube's Google Sites' ReleaseLog """

  # user credentials to login
  user = conf.user
  PASS = conf.PASS
  site = conf.site
  domain = conf.domain
  source = conf.source
  # path to releaselog
  path = conf.path
  last_released = conf.last_released
  proj_dir = conf.proj_dir

  # markup for new entry
  begin_ul = """<div><ul>"""
  begin_li = """<li>"""
  end_li = """</li>"""
  end_ul = """</ul></div>"""
  end_entry = """</div></div></div>"""
  
  def __init__(self):
    self.begin_entry = """<div xmlns:html="http://www.w3.org/1999/xhtml"><div><div><div><b> %s </b></div>""" % (self.now())
    self.getCommitsSinceLastRelease()

  def getCommitsSinceLastRelease(self):
    """ gets the list of commit msgs since the last released commit,
    which is stored in last_released file. """
    f = open(self.last_released, 'r')
    old_rev = f.read().replace('\n', '')
    f.close()
    new_rev = commands.getoutput('cd '+self.proj_dir+' && git log -1 --format=%H')
    cmd = 'cd '+self.proj_dir+' && git log --no-merges --pretty=format:"%s" '+old_rev+'..'+new_rev
    unreleased_commits = commands.getoutput(cmd) 
    print 'Commits since last release:'
    print unreleased_commits
    unreleased_commits = unreleased_commits.split('\n')
    self.commit_msgs = unreleased_commits
    self.new_rev = new_rev

  def now(self):
    """ returns a string of current date time """
    os.environ['TZ'] = conf.timezone
    time.tzset()
    return time.strftime("%B %d %Y %H:%M:%S IST", time.localtime())

  def login(self):
    """ uses jenkins user to login to google sites """
    #create a client class which will make http requests with google docs server.
    print 'Logging in as '+ self.user + '\n'
    self.client = gdata.sites.client.SitesClient(source=self.source, site=self.site, domain=self.domain)
    self.client.ClientLogin(self.user, self.PASS, self.client.source)

  def fetchContent(self):
    """ fetch content of releaselog """
    print 'fetching page by its path: '+ self.path
    uri = '%s?path=%s' % (self.client.MakeContentFeedUri(), self.path)
    # get the content feed
    feed = self.client.GetContentFeed(uri=uri)
    # take out the content
    self.entry = feed.get_webpages()[0]

  def makeNewXml(self):
    """ make a new xml obj from html string """
    new_entry = self.begin_entry + self.begin_ul
    for i in self.commit_msgs:
      i = escape(i)
      li = self.begin_li + i + self.end_li
      new_entry = new_entry + li
    new_entry = new_entry + self.end_ul + self.end_entry
    self.new_xml = atom.core.XmlElementFromString(new_entry)
    
  def insertChild(self):
    """ insert the created xml as the appropriate child node """
    # insert at position 3 as first is heading and next two nodes have some info 
    # from pos 3 the releaselog entry starts
    self.entry.content.html.get_elements('table')[0].get_elements('tbody')[0].get_elements('tr')[0].get_elements('td')[0].get_elements()[0].children.insert(3, self.new_xml)

  # parse all xml into string; replace all 'html:' which causes the pages to break;
  # then create xml object back from string 
  # and finally update self.entry
  def updateXml(self):
    temp_content = self.entry.content.html.to_string()
    temp_content = temp_content.replace('html:', '')
    new_content = atom.core.XmlElementFromString(temp_content)
    self.entry.content.html = new_content

  def updateSites(self):
    """update google sites with the new entry"""
    updated_entry = self.client.Update(self.entry)
    return updated_entry

  def updateLastCommitFile(self):
    """ updates the last_released file with the latest commit """
    f = open(self.last_released, 'w')
    f.write(self.new_rev)
    f.close()

  def run(self):
    self.login()
    self.fetchContent()
    print "Updating content..\n"
    self.makeNewXml()
    self.insertChild()
    self.updateXml()
    updated_entry = self.updateSites()
    if updated_entry is not None:
      print 'Releaselog updated..\n'
      self.updateLastCommitFile()
    else:
      print 'ERROR: Could not update releaselog..\n'


updater = SitesUpdater()
updater.run()
