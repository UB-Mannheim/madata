import sickle
import pandas as pd
import requests
from wikidataintegrator import wdi_core, wdi_login
from tqdm import tqdm
from pprint import pformat
from getpass import getpass

USER_AGENT = 'madata: a tool for syncing the dataset-metadata between MADATA and Wikidata'


class Metadata:
    """
    Class Metadata: It stores the metadata harvested from the MADATA OAI-PMH 
    interface and the metadata for MADATA records taken from the Wikidata
    SPARQL endpoint. It keeps the metadata in sync via Metadata().sync().

    Attributes:
        OAI_DC is a list of metadata records in Dublin Core from MADATA.
               Every metadata record in OAI_DC has subattributes:
               OAI_DC[0].metadata - structured metadata record
               OAI_DC[0].raw - raw metadata record
               OAI_DC[0].header - header for metadata (see OAI_DC[0].header.raw)
        OAI_DC_df is a pandas-dataframe with metadata records.
        URLs is a list of URLs of metadata records at MADATA.
        DOIs is a list of DOIs of metadata records at MADATA.
        QIDs is a list of QIDs of MADATA records at Wikidata.
        QID_DOI_URL is a pandas dataframe with QIDs, DOIs and MADATA URLs of 
                    MADATA metadata records at Wikidata.
    """

    def __init__(self, OAI: str = 'https://madata.bib.uni-mannheim.de/cgi/oai2'):
        if OAI:
            self.OAI: str = OAI
            self._harvest_MADATA_OAI()
            self._get_Wikidata_QIDs()
            self._get_QID_DOI_URL()
            self.attributes = [('OAI', self.OAI),
                               ('MADATA records from OAI-PMH', len(self.OAI_DC)),
                               ('MADATA records at Wikidata', len(self.QIDs)),
                               ('In sync?', len(self.OAI_DC) == len(self.QIDs))]
        else:
            raise ValueError('Incorrect URL for OAI-PMH interface')

    def __repr__(self):
        return pformat(self.attributes)

    def __str__(self):
        return pformat(self.attributes)

    def _harvest_MADATA_OAI(self):
        """Harvests MADATA OAI-PMH interface"""
        try:
            sick = sickle.Sickle(self.OAI)
            self.records = sick.ListRecords(metadataPrefix='oai_dc', ignore_deleted=True)
            self.OAI_DC = list(self.records)
            self.OAI_DC_df = pd.DataFrame([rec.metadata for rec in self.OAI_DC])
            self.OAI_DC_df = self.OAI_DC_df.where(self.OAI_DC_df.notnull(), None)
            self.URLs = [URL.metadata.get('relation')[0] for URL in self.OAI_DC]
            self.DOIs = [DOI.metadata.get('relation')[1] for DOI in self.OAI_DC]
        except Exception as e:
            print(e)

    def _get_QID_DOI_URL(self):
        """
        Get QIDs, DOIs and URLs for all metadata records in the MADATA-subset of
        Wikidata and return pandas-dataframe with them.
        """
        url = "https://query.wikidata.org/sparql"
        try:
            query = """SELECT ?QID ?DOI ?URL WHERE {
              ?QID wdt:P1433 wd:Q118906988.
              OPTIONAL { ?QID wdt:P356 ?DOI. }
              OPTIONAL { ?QID wdt:P856 ?URL. }
            }"""
            r = requests.get(url,
                             params={'format': 'json', 'query': query},
                             headers={'User-Agent': USER_AGENT},
                             timeout=1)
            results = r.json().get('results').get('bindings')
            for prop in results:
                prop.update((key, value.get('value')) for key, value in prop.items())
            if len(results) > 0:
                self.QID_DOI_URL = pd.DataFrame(results, dtype=str)
            else:
                self.QID_DOI_URL = None
        except Exception as e:
            self.QID_DOI_URL = None
            print(e)

    def _get_Wikidata_QIDs(self):
        """
        It returns a list of QIDs of MADATA-records existing at Wikidata.
        """
        url = "https://query.wikidata.org/sparql"
        try:
            query = "SELECT ?item WHERE { ?item wdt:P1433 wd:Q118906988. }"
            r = requests.get(url,
                             params={'format': 'json', 'query': query},
                             headers={'User-Agent': USER_AGENT},
                             timeout=1)
            results = r.json().get('results').get('bindings')
            self.QIDs = []
            for result in results:
                self.QIDs.append(result.get('item').get('value').split('/')[-1])
        except Exception as e:
            self.QIDs = None
            print(e)
        return self.QIDs

    @staticmethod
    def reorder(creator: str = '') -> str:
        "It reorders a string with 'SURNAME, FIRSTNAME' to 'FIRSTNAME SURNAME'"
        [surname, name] = creator.split(',')
        return ' '.join([name, surname])

    def _sync(self):
        """
        If MADATA and MADATA-subset of Wikidata are not in sync, it uploads
        the MADATA metadata to Wikidata.
        """
        WDUSER = getpass(prompt="Wikidata username: ")
        WDPASS = getpass(prompt="Wikidata password: ")
        login = wdi_login.WDLogin(WDUSER, WDPASS)

        for index, row in tqdm(self.OAI_DC_df.iterrows()):
            MADATA_URL, DOI = row.relation
            if MADATA_URL not in list(self.QID_DOI_URL.URL):
                creators = [self.reorder(c).strip() for c in row.creator]
                data = [wdi_core.WDItemID('Q1172284', prop_nr='P31'), # instance of dataset
                        wdi_core.WDMonolingualText(row.title[0].strip(), prop_nr='P1476')] # title
                for i, creator in enumerate(creators):
                    qualifiers = [wdi_core.WDString(str(i + 1), prop_nr='P1545', is_qualifier=True)]
                    data.append(
                        wdi_core.WDString(creator, prop_nr='P2093', qualifiers=qualifiers))  # author name string
                data.append(wdi_core.WDItemID('Q1860', prop_nr='P407'))  # language of work or name is English
                data.append(wdi_core.WDUrl(MADATA_URL, prop_nr='P856'))  # official website is MADATA_URL
                if row.get('subject'):
                    for subject in row.subject:  # Dewey Decimal Classification (works and editions)
                        data.append(wdi_core.WDString(subject[0:3], prop_nr='P8359'))
                data.append(wdi_core.WDItemID('Q118906988', prop_nr='P1433'))  # published in MADATA
                if row.get('ubma_language'):
                    for language in row.ubma_language:  # language of work or name is
                        if language == 'eng':
                            data.append(wdi_core.WDItemID('Q1860', prop_nr='P407'))
                        if language == 'ger':
                            data.append(wdi_core.WDItemID('Q188', prop_nr='P407'))
                        if language == 'fre':
                            data.append(wdi_core.WDItemID('Q150', prop_nr='P407'))
                if row.description:
                    abstract = row.description[0][0:1500].strip() # Wikidata allow only 1500 symbols
                    data.append(wdi_core.WDMonolingualText(abstract, prop_nr='P7535')) # scope and content for abstract
                if row.get('rights'):
                    rights = list(set(row.rights))
                    for right in rights:
                        if right == 'cc0':
                            data.append(wdi_core.WDItemID('Q6938433', prop_nr='P275'))
                        if right == 'cc_by_nc_sa':  # Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported
                            data.append(wdi_core.WDItemID('Q15643954', prop_nr='P275'))
                        if right == 'cc_by_nc_sa_4':  # Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
                            data.append(wdi_core.WDItemID('Q42553662', prop_nr='P275'))
                        if right == 'cc_by_4':  # Creative Commons Attribution 4.0 International
                            data.append(wdi_core.WDItemID('Q20007257', prop_nr='P275'))
                        if right == 'cc_by_sa_4':  # Creative Commons Attribution-ShareAlike 4.0 International
                            data.append(wdi_core.WDItemID('Q18199165', prop_nr='P275'))
                        if right == 'cc_by_nc_nd':  # Creative Commons Attribution-NonCommercial-NoDerivs 3.0 Unported
                            data.append(wdi_core.WDItemID('Q19125045', prop_nr='P275'))
                        if right == 'cc_by_nc_nd_4':  # Creative Commons Attribution-NonCommercial-NoDerivs 4.0 International
                            data.append(wdi_core.WDItemID('Q24082749', prop_nr='P275'))
                        if right == 'cc_by':  # Creative Commons Attribution 3.0 Unported
                            data.append(wdi_core.WDItemID('Q14947546', prop_nr='P275'))
                        if right == 'cc_by_sa':  # Creative Commons Attribution-ShareAlike 3.0 Unported
                            data.append(wdi_core.WDItemID('Q14946043', prop_nr='P275'))
                        if right == 'cc_by_nd_4':  # Creative Commons Attribution-NoDerivs 4.0 International
                            data.append(wdi_core.WDItemID('Q36795408', prop_nr='P275'))
                data.append(wdi_core.WDExternalID(DOI, prop_nr='P356'))  # DOI
                if row.get('identifier'):
                    for ident in row.identifier:
                        if ident.startswith('https://madata'):
                            data.append(wdi_core.WDUrl(ident, prop_nr='P4945'))  # download link
                if row.get('ubma_url_external'):
                    for URLext in row.get('ubma_url_external'):
                        data.append(wdi_core.WDUrl(URLext, prop_nr='P973'))  # described at
                try:
                    wd_item = wdi_core.WDItemEngine(data=data)
                    wd_item.set_label(label=row.title[0].strip())  # set label
                    if row.get('ubma_additional_title'):
                        wd_item.set_description(description=row.ubma_additional_title[0].strip())  # set description
                    wd_item.write(login, bot_account=False)
                except Exception as e:
                    print(e)
            else:
                print('DOI: ' + DOI + ' is already at Wikidata for the MADATA record at: ' + MADATA_URL)
