'''
Created on 18.05.2013

@author: anteru
'''
import unittest

import Liara

class MockItemReader(Liara.FilesystemReader):
    def __init__(self):
        self._items = []
    
    def AddItem (self, item):
        self._items.append (item)
    
    def GetItems (self):
        return self._items

class Test (unittest.TestCase):
    def setUp (self):
        self.reader = MockItemReader ()
        self.textItem = Liara.Item('/test', 'Test',
            {'content-type' : 'text'})
        self.reader.AddItem (self.textItem)
        
        self.reader.AddItem (Liara.Item ('/test/a', 'Test-A',
            {'content-type' : 'text'}))
        self.reader.AddItem (Liara.Item ('/test/b', 'Test-B',
            {'content-type' : 'text'}))        
        self.reader.AddItem (Liara.Item ('/other', 'Test-Other',
            {'content-type' : 'text'}))

        self.site = Liara.Site (self.reader)
    
    def testReaderItemsAreRead (self):
        self.assertIsNotNone(self.site.GetItem('/test'))
        
    def testGetItemReturnsNoneForNonExistingItem (self):
        self.assertIsNone(self.site.GetItem ('/bla'))
        
    def testGetItemByFilter (self):
        items = list (self.site.GetItems('/test/*'))
        self.assertEqual(2, len (items))
        
    def testGetItemByFilterForNonExistingPath (self):
        items = list (self.site.GetItems ('/non-exist'))
        self.assertEqual(0, len(items))
        
    def testGetItemWorks (self):
        self.assertEqual(self.textItem, self.site.GetItem('/test'))

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()