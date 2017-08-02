from lxml import etree

from pyfomod import parser, validation


class Test_FomodElement:
    def test_compare(self):
        elem_std = etree.fromstring("<a boo=\"2\" goo=\"5\">text<b/>tail</a>",
                                    parser=parser.FOMOD_PARSER)
        elem_ord = etree.fromstring("<a goo=\"5\" boo=\"2\">text<b/>tail</a>",
                                    parser=parser.FOMOD_PARSER)
        assert elem_std.compare(elem_std, elem_ord)

        elem_atr = etree.fromstring("<a boo=\"4\" goo=\"5\">text<b/>tail</a>",
                                    parser=parser.FOMOD_PARSER)
        assert not elem_std.compare(elem_std, elem_atr)

        elem_tail = etree.fromstring("<a boo=\"2\" goo=\"5\">text<b/>err</a>",
                                     parser=parser.FOMOD_PARSER)
        assert not elem_std[0].compare(elem_std[0], elem_tail[0])

        elem_text = etree.fromstring("<a boo=\"2\" goo=\"5\">err<b/>tail</a>",
                                     parser=parser.FOMOD_PARSER)
        assert not elem_std.compare(elem_std, elem_text)

        elem_tag = etree.fromstring("<c boo=\"2\" goo=\"5\">text<b/>tail</c>",
                                    parser=parser.FOMOD_PARSER)
        assert not elem_std.compare(elem_std, elem_tag)

        elem_len = etree.fromstring("<a boo=\"2\" goo=\"5\">"
                                    "text<b/><c/>tail</a>",
                                    parser=parser.FOMOD_PARSER)
        assert not elem_std.compare(elem_std, elem_len, True)

        elem_cld = etree.fromstring("<a boo=\"2\" goo=\"5\">text<c/>tail</a>",
                                    parser=parser.FOMOD_PARSER)
        assert not elem_std.compare(elem_std, elem_cld, True)

    def test_setup(self, single_parse):
        for elem in single_parse[0].iter(tag=etree.Element):
            elem._setup(validation.INFO_SCHEMA_TREE)
            assert parser.FomodElement.compare(elem.schema,
                                               validation.INFO_SCHEMA_TREE)

        for elem in single_parse[1].iter(tag=etree.Element):
            elem._setup(validation.CONF_SCHEMA_TREE)
            assert parser.FomodElement.compare(elem.schema,
                                               validation.CONF_SCHEMA_TREE)

    def test_lookup_element(self, single_parse):
        info_schema = validation.INFO_SCHEMA_TREE
        conf_schema = validation.CONF_SCHEMA_TREE

        root = single_parse[0]
        root._setup(info_schema)
        root._lookup_element()
        current_lookups = (root.schema_element,
                           root.schema_type)
        assert parser.FomodElement.compare(current_lookups[0], info_schema[0])
        assert parser.FomodElement.compare(current_lookups[1],
                                           info_schema[0][1])

        name = single_parse[0][1]
        name._setup(info_schema)
        name._lookup_element()
        current_lookups = (name.schema_element,
                           name.schema_type)
        assert parser.FomodElement.compare(current_lookups[0],
                                           info_schema[0][1][0][0])
        assert parser.FomodElement.compare(current_lookups[1],
                                           info_schema[0][1][0][0])

        config = single_parse[1]
        config._setup(conf_schema)
        config._lookup_element()
        current_lookups = (config.schema_element,
                           config.schema_type)
        assert parser.FomodElement.compare(current_lookups[0],
                                           conf_schema[-1])
        assert parser.FomodElement.compare(current_lookups[1],
                                           conf_schema[-2])


class Test_FomodLookup:
    def test_base_class(self, single_parse):
        for tree in single_parse:
            for element in tree.iter(tag=etree.Element):
                assert isinstance(element, parser.FomodElement)

    def test_subclasses(self, single_parse):
        root = single_parse[1]
        assert isinstance(root, parser.Root)
        mod_dep = root.findall('.//moduleDependencies')
        assert(all(isinstance(elem, parser.Dependencies)) for elem in mod_dep)
        dep = root.findall('.//dependencies')
        assert(all(isinstance(elem, parser.Dependencies)) for elem in dep)
        vis = root.findall('.//visible')
        assert(all(isinstance(elem, parser.Dependencies)) for elem in vis)
        step = root.findall('.//installStep')
        assert(all(isinstance(elem, parser.InstallStep)) for elem in step)
        group = root.findall('.//group')
        assert(all(isinstance(elem, parser.Group)) for elem in group)
        plugin = root.findall('.//plugin')
        assert(all(isinstance(elem, parser.Plugin)) for elem in plugin)
        tp_dep = root.findall('.//dependencyType')
        assert(all(isinstance(elem, parser.TypeDependency)) for elem in tp_dep)
        tp_pat = root.findall('.//pattern/type')
        assert(all(isinstance(elem, parser.TypePattern)) for elem in tp_pat)
        fl_pat = root.findall('.//pattern/files')
        assert(all(isinstance(elem, parser.InstallPattern)) for elem in fl_pat)