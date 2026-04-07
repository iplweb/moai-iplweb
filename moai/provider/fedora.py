import os
import hashlib
import base64
from urllib import request as urllib_request
from urllib.error import HTTPError

from lxml import etree

from moai.provider.oai import OAIBasedContentProvider


class FOXMLFile(object):
    def __init__(self, file_obj):
        self._doc = etree.parse(file_obj)
        self._ns = "info:fedora/fedora-system:def/foxml#"

    def get_property(self, name):
        properties = self._doc.xpath(
            '//foxml:property[@NAME="%s"]' % name,
            namespaces={"foxml": self._ns},
        )
        if not properties:
            return
        value = properties[-1].get("VALUE")
        if value:
            return value

    def get_xml_ids(self):
        ids = self._doc.xpath(
            '//foxml:datastream[@CONTROL_GROUP="X"]/@ID',
            namespaces={"foxml": self._ns},
        )
        return list(ids)

    def get_ids(self):
        ids = self._doc.xpath(
            "//foxml:datastream/@ID",
            namespaces={"foxml": self._ns},
        )
        return list(ids)

    def get_xml(self, id):
        contents = self._doc.xpath(
            ('//foxml:datastream[@CONTROL_GROUP="X" and @ID="%s"]/foxml:datastreamVersion/foxml:xmlContent' % id),
            namespaces={"foxml": self._ns},
        )
        if not contents:
            return
        for child in contents[-1]:
            xml = etree.tostring(child, encoding="unicode", pretty_print=True)
            break
        return xml.strip()

    def get_location(self, id):
        locations = self._doc.xpath(
            ('//foxml:datastream[@ID="%s"]/foxml:datastreamVersion/foxml:contentLocation[@TYPE="URL"]/@REF' % id),
            namespaces={"foxml": self._ns},
        )
        if not locations:
            return
        return str(locations[-1])

    def get_digest(self, id):
        digests = self._doc.xpath(
            ('//foxml:datastream[@ID="%s"]/foxml:datastreamVersion/foxml:contentDigest[@TYPE="MD5"]/@DIGEST' % id),
            namespaces={"foxml": self._ns},
        )
        if not digests:
            return
        return str(digests[-1])

    def get_mimetype(self, id):
        mimes = self._doc.xpath(
            ('//foxml:datastream[@ID="%s"]/foxml:datastreamVersion/@MIMETYPE' % id),
            namespaces={"foxml": self._ns},
        )
        if not mimes:
            return
        return str(mimes[-1])

    def get_label(self, id):
        labels = self._doc.xpath(
            ('//foxml:datastream[@ID="%s"]/foxml:datastreamVersion/@LABEL' % id),
            namespaces={"foxml": self._ns},
        )
        if not labels:
            return
        return str(labels[-1])


class FedoraBasedContentProvider(OAIBasedContentProvider):
    """Providers content by harvesting a Fedora Commons OAI feed.
    Then uses the content from a specific datastream, or retrieves the
    full foxml file if no datastream is provided
    Implements the :ref:`IContentProvider` interface
    """

    def __init__(self, fedora_url, output_path, datastream_name=None, username=None, password=None):
        oai_url = "%s/oai" % fedora_url
        super().__init__(oai_url, output_path)
        self._stream = datastream_name
        self._fedora_url = fedora_url
        self._user = username
        self._pass = password
        if not os.path.isdir(output_path):
            os.mkdir(output_path)

    def _get_id(self, header):
        fedora_id = ":".join(header.identifier().split(":")[2:])
        return fedora_id

    def _process_record(self, header, element):
        fedora_id = self._get_id(header)

        if self._stream is None:
            url = "%s/objects/%s/objectXML" % (self._fedora_url, fedora_id)
        else:
            # get only a specific data stream
            url = "%s/get/%s/%s" % (self._fedora_url, fedora_id, self._stream)

        if self._user and self._pass:
            credentials = ("%s:%s" % (self._user, self._pass)).encode("ascii")
            password = base64.b64encode(credentials).decode("ascii")
            headers = {"Authorization": "Basic %s" % password}
            req = urllib_request.Request(url, headers=headers)
        else:
            req = urllib_request.Request(url)

        try:
            fp = urllib_request.urlopen(req)
            xml_data = fp.read()
            fp.close()
        except HTTPError as err:
            self._log.warning("HTTP %s -> Can not get Fedora data: %s" % (err.code, url))
            return False

        directory = hashlib.md5(fedora_id.encode("utf-8")).hexdigest()[:3]

        path = os.path.join(self._path, directory)
        if not os.path.isdir(path):
            os.mkdir(path)

        path = os.path.join(path, "%s.xml" % fedora_id)

        with open(path, "wb") as fp:
            fp.write(xml_data)
        return True
