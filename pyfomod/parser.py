# Copyright 2016 Daniel Nunes
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module holds the custom parser and the key classes necessary
for the api.
"""

from collections import namedtuple
from copy import deepcopy

from lxml import etree

import pyfomod

_Attribute = namedtuple('_Attribute', "name doc default type use restriction")
"""
This ``namedtuple`` represents a single possible attribute for a FomodElement.

Attributes:
    name (str): The identifier of this attribute.
    doc (str): The schema documentation for this attribute.
    default (str or None): The default value for this attribute or None if
        none is specified.
    type (str): The type of this attribute's value.
    use (str): Either ``'optional'``, ``'required'`` or ``'prohibited'``.
    restriction (_AttrRestriction): A namedtuple with the attribute's
        restrictions. For more info refer to :py:class:`_AttrRestriction`.
"""

_ATTR_REST_ATTRIBUTES = "type enum_list decimals length max_exc max_inc " \
                        "max_len min_exc min_inc min_len pattern total_digits"
_AttrRestriction = namedtuple('_AttrRestriction', _ATTR_REST_ATTRIBUTES)
"""
This ``namedtuple`` represents a single attribute's value restrictions.
For more information about restrictions refer to `W3Schools`_.

.. _W3Schools: https://www.w3schools.com/xml/schema_facets.asp

Attributes:
    type (str): A string containing all restriction types separated by a
        single whitespace. Example: ``'max_length min_length '``
    enum_list (list(_AttrRestElement)): A list of possible values for this
        attribute.

Warning:
    Since none of the other restriction types occur in the actual schemas
    all other attributes are always set to :py:class:`None`.
"""

_AttrRestElement = namedtuple('_AttrRestElement', 'value doc')
"""
This ``namedtuple`` represents a single value for a restriction.

Attributes:
    value (str): The string containing the value.
    doc (str): The schema documentation for this value.
"""

_ORDER_INDICATOR_ATTRIBUTES = 'type element_list max_occ min_occ'
_OrderIndicator = namedtuple('_OrderIndicator', _ORDER_INDICATOR_ATTRIBUTES)
"""
This ``namedtuple`` represents an order indicator in the element's schema.
For more information about order indicators refer to `W3Schools`_.

.. _W3Schools: https://www.w3schools.com/xml/schema_facets.asp

Attributes:
    type (str): Either ``'sequence'``, ``'choice'`` or ``'all'``.
    element_list (list): A list of :py:class:`_OrderIndicator` and
        :py:class:`_ChildElement` that translates an order of valid children.
    max_occ (int): The maximum number of times this order can occur in a row.
    min_occ (int): The minimum number of times this order can occur in a row.
"""

_ChildElement = namedtuple('_ChildElement', 'tag max_occ min_occ')
"""
This ``namedtuple`` represents a valid child of an element.

Attributes:
    tag (str): The tag of the possible child.
    max_occ (int): The maximum number of times this child can occur in a row.
    min_occ (int): The minimum number of times this child can occur in a row.
"""


class FomodElement(etree.ElementBase):
    """
    The base class for all FOMOD elements. This, along with the lxml API,
    serves as the low-level API for pyfomod.

    Attributes:
        _schema (lxml.etree._Element): The schema this element belongs to.
        _schema_element (lxml.etree._Element): The element in the schema this
            element corresponds to.
        _schema_type (lxml.etree._Element): The type that corresponds to
            `_schema_element`. Usually this will be a *complexType* but can be
            the same as `_schema_element` if it's a simple element.
    """

    @property
    def max_occurences(self):
        """
        int or None:
            Returns the maximum times this element can be
            repeated or ``None`` if there is no limit.
        """
        return self._element_get_max_occurs(self._schema_element)

    @property
    def min_occurences(self):
        """
        int:
            Returns the minimum times this element has to be repeated.
        """
        return int(self._schema_element.get('minOccurs', 1))

    @property
    def type(self):
        """
        str or None:
            The text type of this element. :py:class:`None` if no text is
            allowed.
        """
        if self._schema_element is self._schema_type:
            return self._schema_type.get('type')[3:]

        nsmap = '{' + self._schema.nsmap['xs'] + '}'
        content_exp = "{}simpleContent".format(nsmap)
        content = self._schema_type.find(content_exp)

        if content is None:
            return None

        type_exp = "xs:extension | xs:restriction"
        base_elem = content.xpath(type_exp, namespaces=self._schema.nsmap)[0]
        return base_elem.get('base')[3:]

    @property
    def comment(self):
        """
        str:
            The text of this element' comment.
            If no comment exists when setting new text, a comment is created.
        """
        if self._comment is None:
            return ""
        return self._comment.text

    @comment.setter
    def comment(self, text):
        if self._comment is None:
            self.addprevious(etree.Comment(text))

            # pylint: disable=attribute-defined-outside-init
            self._comment = self.getprevious()
        else:
            self._comment.text = text

    @property
    def doc(self):
        """
        str:
            Returns the documentation text associated with this element
            in the schema.
        """
        doc = self._get_schema_doc(self._schema_element)
        if doc is None:
            return ""
        return doc

    @staticmethod
    def _element_get_max_occurs(element):
        """
        Returns maxOccurs for the specified element. None if unbounded.
        """
        max_occ = element.get('maxOccurs', 1)
        if max_occ == 'unbounded':
            return None
        return int(max_occ)

    @staticmethod
    def _get_schema_doc(schema_elem):
        """
        Returns the text of the of the annotation/documentation element
        below the `schema_elem`. Example::

            <`schema_elem`>
                <annotation>
                    <documentation>
                        This method returns this.
                    </documentation>
                </annotation>
            </`schema_elem`>

        If no such structure could be found, returns ``None``.
        """
        nsmap = '{' + schema_elem.nsmap['xs'] + '}'
        doc_elem = schema_elem.find("{0}annotation/"
                                    "{0}documentation".format(nsmap))
        if doc_elem is not None:
            return doc_elem.text
        return None

    @staticmethod
    def _get_order_from_group(group_elem, root_elem):
        """
        Returns the order indicator from a group reference.
        """
        nsmap = '{' + root_elem.nsmap['xs'] + '}'
        ord_exp = "xs:all | xs:sequence | xs:choice"
        group_ref_exp = "{}group[@name=\"{}\"]".format(nsmap,
                                                       group_elem.get('ref'))

        group_ref = root_elem.find(group_ref_exp)
        return group_ref.xpath(ord_exp,
                               namespaces=root_elem.nsmap)[0]

    @classmethod
    def _valid_children_parse_order(cls, ord_elem):
        """
        Parses the *ord_elem* order indicator.
        Needs to be separate from the main method to be recurrent.
        Returns an _OrderIndicator named tuple for the *ord_elem*.
        """
        child_list = []
        child_exp = 'xs:element | xs:all | xs:sequence | xs:choice'
        nsmap = '{' + ord_elem.nsmap['xs'] + '}'

        for child in ord_elem.xpath(child_exp, namespaces=ord_elem.nsmap):
            child_tuple = None
            if child.tag == '{}element'.format(nsmap):
                child_max_occ = cls._element_get_max_occurs(child)
                child_tuple = _ChildElement(child.get('name'),
                                            child_max_occ,
                                            int(child.get('minOccurs', 1)))
            else:
                child_tuple = cls._valid_children_parse_order(child)
            child_list.append(child_tuple)

        return _OrderIndicator(etree.QName(ord_elem).localname, child_list,
                               cls._element_get_max_occurs(ord_elem),
                               int(ord_elem.get('minOccurs', 1)))

    def _init(self):
        """
        Used to setup the class, instead of an __init__
        since lxml doesn't let us use it.
        """
        # pylint: disable=attribute-defined-outside-init

        # the schema this element belongs to
        self._schema = pyfomod.FOMOD_SCHEMA_TREE

        # the element that holds minOccurs, etc.
        self._schema_element = None

        # the type of this element (can be the same as the schema_element)
        # holds info about attributes, children, etc.
        self._schema_type = None

        lookup = self._lookup_element()
        self._schema_element, self._schema_type = lookup

        # the comment associated with this element.
        # this comment always exists before the element.
        self._comment = None
        if (self.getprevious() is not None and
                self.getprevious().tag is etree.Comment):
            self._comment = self.getprevious()

    def _lookup_element(self):
        """
        Looks up the corresponding element/complexType in the corresponding
        schema. Serves as base for all other lookups.
        """
        ancestor_list = list(self.iterancestors())[::-1]
        ancestor_list.append(self)
        nsmap = '{' + self._schema.nsmap['xs'] + '}'

        # the current element in schema
        # in most cases it will actually be a complexType
        current_element = self._schema

        # the holder element will always be an actual element
        # it will contain tag, minOccurs, maxOccurs, etc.
        holder_element = None

        for elem in ancestor_list:
            xpath_exp = "{}element[@name=\"{}\"]".format(nsmap, elem.tag)
            holder_element = current_element.find(xpath_exp)

            # this means there could order tags and/or be nested in a group tag
            if holder_element is None:
                ord_exp = "xs:all | xs:sequence | xs:choice"

                # check group tag first
                group_elem = current_element.find('{}group'.format(nsmap))
                if group_elem is not None:
                    first = [self._get_order_from_group(group_elem,
                                                        self._schema)]
                else:
                    namespaces = self._schema.nsmap
                    first = current_element.xpath(ord_exp,
                                                  namespaces=namespaces)

                # check for order tags
                while holder_element is None and first:
                    temp = first
                    holder_element = temp[0].find(xpath_exp)
                    first = first[0].xpath(ord_exp,
                                           namespaces=self._schema.nsmap)

            # a complexType that is used solely for this element
            if holder_element.get('type') is None:
                complex_exp = '{}complexType'.format(nsmap)
                current_element = holder_element.find(complex_exp)

            # it is vital that this is the last element
            # if not, then the xml is not valid and something is wrong
            # with this code
            elif holder_element.get('type').startswith('xs:'):
                current_element = holder_element

            # last, the complex type is separate from the holder element
            else:
                custom_type = holder_element.get('type')
                complx_exp = '{}complexType[@name=\"{}\"]'.format(nsmap,
                                                                  custom_type)
                current_element = self._schema.find(complx_exp)

        return holder_element, current_element

    def valid_attributes(self):
        """
        Gets all possible attributes of this element
        along with some extra info in the
        :py:class:`namedtuple <collections.namedtuple>`.

        Returns:
            list(_Attribute):
                A list of all possible attributes
                this element can have. For more info refer to
                :py:class:`_Attribute`.
        """
        nsmap = '{' + self._schema.nsmap['xs'] + '}'
        result_list = []

        attr_list = self._schema_type.findall("{}attribute".format(nsmap))

        # this is a mixed complex element, has text and attr
        if not attr_list:
            attr_exp = "xs:simpleContent/xs:extension/xs:attribute | " \
                       "xs:simpleContent/xs:restriction/xs:attribute"
            attr_list = self._schema_type.xpath(attr_exp,
                                                namespaces=self._schema.nsmap)

        for attr in attr_list:
            name = attr.get('name')

            doc = self._get_schema_doc(attr)

            default = attr.get('default')

            use = attr.get('use', 'optional')

            attr_type = attr.get('type')
            restriction = None

            # this is a builtin type
            if attr_type is not None and attr_type.startswith('xs:'):
                attr_type = attr_type[3:]

            else:
                restriction_element = None

                # the attribute has a simpleType below
                if attr_type is None:
                    rest_exp = '{0}simpleType/{0}restriction'.format(nsmap)
                    restriction_element = attr.find(rest_exp)

                # finally this is a custom separate type
                else:
                    type_exp = '{}simpleType[@name=\"{}\"]'.format(nsmap,
                                                                   attr_type)
                    rest_exp = '{}/{}restriction'.format(type_exp, nsmap)
                    restriction_element = self._schema.find(rest_exp)

                attr_type = restriction_element.get('base')[3:]
                rest_type = ''
                enum_list = []
                # decimals = None
                # length = None
                # max_exc = None
                # max_inc = None
                # max_len = None
                # min_exc = None
                # min_inc = None
                # min_len = None
                # pattern = None
                # total_digits = None

                for child in restriction_element:
                    doc_child = self._get_schema_doc(child)
                    value = child.get('value')

                    rest_tuple = _AttrRestElement(value, doc_child)

                    if child.tag == '{}enumeration'.format(nsmap):
                        if 'enumeration' not in rest_type:
                            rest_type += 'enumeration '
                        enum_list.append(rest_tuple)

                    # elif child.tag == '{}fractionDigits'.format(nsmap):
                    #     if 'decimals' not in rest_type:
                    #         rest_type += 'decimals '
                    #     decimals = rest_tuple

                    # elif child.tag == '{}length'.format(nsmap):
                    #     if 'length' not in rest_type:
                    #         rest_type += 'length '
                    #     length = rest_tuple

                    # elif child.tag == '{}maxExclusive'.format(nsmap):
                    #     if 'max_exclusive' not in rest_type:
                    #         rest_type += 'max_exclusive '
                    #     max_exc = rest_tuple

                    # elif child.tag == '{}maxInclusive'.format(nsmap):
                    #     if 'max_inclusive' not in rest_type:
                    #         rest_type += 'max_inclusive '
                    #     max_inc = rest_tuple

                    # elif child.tag == '{}maxLength'.format(nsmap):
                    #     if 'max_length' not in rest_type:
                    #         rest_type += 'max_length '
                    #     max_len = rest_tuple

                    # elif child.tag == '{}minExclusive'.format(nsmap):
                    #     if 'min_exclusive' not in rest_type:
                    #         rest_type += 'min_exclusive '
                    #     min_exc = rest_tuple

                    # elif child.tag == '{}minInclusive'.format(nsmap):
                    #     if 'min_inclusive' not in rest_type:
                    #         rest_type += 'min_inclusive '
                    #     min_inc = rest_tuple

                    # elif child.tag == '{}minLength'.format(nsmap):
                    #     if 'min_length' not in rest_type:
                    #         rest_type += 'min_length '
                    #     min_len = rest_tuple

                    # elif child.tag == '{}pattern'.format(nsmap):
                    #     if 'pattern' not in rest_type:
                    #         rest_type += 'pattern '
                    #     pattern = rest_tuple

                    # elif child.tag == '{}totalDigits'.format(nsmap):
                    #     if 'total_digits' not in rest_type:
                    #         rest_type += 'total_digits '
                    #     total_digits = rest_tuple

                # restriction = AttrRestriction(rest_type, enum_list, decimals,
                #                               length, max_exc, max_inc,
                #                               max_len, min_exc, min_inc,
                #                               min_len, pattern, total_digits)
                restriction = _AttrRestriction(rest_type, enum_list, None,
                                               None, None, None,
                                               None, None, None,
                                               None, None, None)

            result_list.append(_Attribute(name, doc, default, attr_type,
                                          use, restriction))

        return result_list

    def required_attributes(self):
        """
        Utility method that returns only attributes that are required
        by this element.

        Returns:
            list(_Attribute): The list of required attributes.
        """
        valid_attrib = self.valid_attributes()
        return [attr for attr in valid_attrib if attr.use == 'required']

    def _find_valid_attribute(self, name):
        """
        Checks if possible attribute name is possible within the schema.
        Returns the _Attribute namedtuple for the possible attribute.
        If there is no possible attribute, raises ValueError.
        """
        valid_attrs = self.valid_attributes()
        possible_attr = None
        for attr in valid_attrs:
            if attr.name == name:
                possible_attr = attr
                break

        if possible_attr is None:
            raise ValueError("No valid attribute with name {}".format(name))
        else:
            return possible_attr

    def get_attribute(self, name):
        """
        Args:
            name (str): The attribute's name.

        Returns:
            The attribute's value.

        Raises:
            ValueError: If the attribute is not allowed by the schema.
        """
        existing_attr = self.get(name)
        if existing_attr is not None:
            return existing_attr

        default_attr = self._find_valid_attribute(name)
        if default_attr.default is not None:
            return default_attr.default
        return ""

    def set_attribute(self, name, value):
        """
        Args:
            name (str): The attribute's name.
            value (str): The attribute's value.

        Raises:
            ValueError: If the attribute is not allowed by the schema or
                if the value is not allowed by the attribute's restrictions.
        """
        possible_attr = self._find_valid_attribute(name)
        if possible_attr.restriction is not None:
            if 'enumeration' in possible_attr.restriction.type:
                enum_list = possible_attr.restriction.enum_list
                if value not in [enum.value for enum in enum_list]:
                    raise ValueError("{} is not allowed by this "
                                     "attribute's restrictions.".format(value))

        self.set(name, value)

    def valid_children(self):
        """
        Gets all the possible, valid children for this element.

        Returns:
            _OrderIndicator or None:
                This :py:class:`namedtuple <collections.namedtuple>` contains
                the valid children for this element. For more information on
                its structure refer to :py:class:`_OrderIndicator`.
                `None` if this element has no valid children.
        """
        nsmap = '{' + self._schema.nsmap['xs'] + '}'

        # if it's a simple element, no children
        if self._schema_type is self._schema_element:
            return None

        # the order tuple to return
        initial_ord = None

        # the valid order indicators
        order_indicators = ['all', 'sequence', 'choice']

        first_exp = 'xs:group | xs:all | xs:sequence | xs:choice'
        first = self._schema_type.xpath(first_exp,
                                        namespaces=self._schema.nsmap)[0]

        if first.tag == '{}group'.format(nsmap):
            first = self._get_order_from_group(first, self._schema)

        if etree.QName(first).localname in order_indicators:
            initial_ord = self._valid_children_parse_order(first)

        return initial_ord

    def _required_children_choice(self, choice):
        """
        Returns the required children of a choice order indicator.
        Always selects the first path in the choice, regardless of
        the actual children.
        It's probably a good idea to eventually try to make it choose
        the corrent path based on the existing children.
        """
        req_child = []
        try:
            selected_path = choice.element_list[0]
        except IndexError:
            return []

        if isinstance(selected_path, _OrderIndicator):
            if selected_path.type == 'choice':
                req_child.extend(self._required_children_choice(selected_path))
            else:
                req_child.extend(
                    self._required_children_sequence(selected_path))
        elif selected_path.min_occ > 0:
            req_child.append((selected_path.tag, selected_path.min_occ))

        for index in range(0, len(req_child)):
            req_child[index] = (req_child[index][0],
                                req_child[index][1] * choice.min_occ)

        return req_child

    def _required_children_sequence(self, sequence):
        """
        Returns the required children of a sequence order indicator.
        """
        req_child = []

        for elem in sequence.element_list:
            if isinstance(elem, _OrderIndicator):
                if elem.type == 'choice':
                    req_child.extend(self._required_children_choice(elem))
                else:
                    req_child.extend(self._required_children_sequence(elem))
            elif elem.min_occ > 0:
                req_child.append((elem.tag, elem.min_occ))

        for index in range(0, len(req_child)):
            req_child[index] = (req_child[index][0],
                                req_child[index][1] * sequence.min_occ)

        return req_child

    def required_children(self):
        """
        Returns a list with the required children by this element.
        Currently, this assumes no children exist and whenever there
        is a choice to be made it always chooses the first path.

        Returns:
            list(tuple(string, int)): A list of tuples as
                (child tag, child minimum occurences).
        """
        valid_children = self.valid_children()
        if valid_children is None:
            return []
        elif valid_children.type == 'choice':
            return self._required_children_choice(valid_children)
        return self._required_children_sequence(valid_children)

    def _setup_shallow_schema_and_self(self):
        """
        Returns a shallow copy of the schema corresponding to this element
        and a shallow copy of this element and its children.
        """
        schema_elem = etree.Element(etree.QName(self._schema_element,
                                                'schema'),
                                    nsmap=self._schema_element.nsmap)

        schema_type = deepcopy(self._schema_element)
        schema_elem.append(schema_type)
        if self._schema_element.get('type') is not None:
            schema_type = deepcopy(self._schema_type)
            schema_elem.append(schema_type)

        if self._schema_element is not self._schema_type:
            for elem in schema_type.iter(tag='{*}element'):
                if elem is schema_type:
                    continue
                elem.attrib.pop('type', None)
                for grandchild in elem:
                    elem.remove(grandchild)

        self_copy = etree.Element(self.tag)
        for elem in self:
            etree.SubElement(self_copy, elem.tag)

        return schema_elem, self_copy

    def _find_possible_index(self, tag):
        """
        Tries to figure out if a child can be added to this element,
        and if it can, what index it should be inserted at.

        To this end, a shallow copy of this element's schema correspondence
        and it's possible children is performed.
        After, the same is done to this element and it's real children.
        A test element with the child's tag is created.
        This test element is then inserted at every possible position in the
        copy of self (reversed order) until a valid position is found.
        """
        schema_elem, self_copy = self._setup_shallow_schema_and_self()

        test_elem = etree.Element(tag)
        schema = etree.XMLSchema(schema_elem)

        self_copy.append(test_elem)
        if schema.validate(self_copy):
            return -1

        for index in reversed(range(len(self_copy))):
            self_copy.insert(index, test_elem)
            if schema.validate(self_copy):
                return index

        return None

    def can_add_child(self, child):
        """
        Checks if a given child can be possibly added to this element.

        Args:
            child (str or FomodElement): The tag or the actual child to add.

        Returns:
            bool: Whether the child can be added or not.

        Raises:
            TypeError: If child is neither a string nor FomodElement.

        Warning:
            This method and its corresponding :func:`~FomodElement.add_child`
            can both possibly be performance heavy on elements with large
            numbers of children.

            It is therefore recommended to use this pattern::

                try:
                    element.add_child(child)
                except ValueError:
                    pass

            Instead of::

                if element.can_add_child(child):
                    element.add_child(child)
        """
        tag = ""
        if isinstance(child, str):
            tag = child
        elif isinstance(child, FomodElement):
            tag = child.tag
        else:
            raise TypeError("Only tags (string) and elements (FomodElement)"
                            " are accepted as arguments.")

        if self._find_possible_index(tag) is None:
            return False
        return True

    def add_child(self, child):
        """
        Adds a child to this element.

        Args:
            child (str or FomodElement): The tag or the actual child to add.

        Raises:
            TypeError: If child is neither a string nor FomodElement.
            ValueError: If the child cannot be added to this element.
        """
        tag = ""
        child_is_tag = False
        if isinstance(child, str):
            tag = child
            child_is_tag = True
        elif isinstance(child, FomodElement):
            tag = child.tag
        else:
            raise TypeError("Only tags (string) and elements (FomodElement)"
                            " are accepted as arguments.")

        index = self._find_possible_index(tag)
        if index is None:
            raise ValueError("child argument cannot be added to this element.")

        if child_is_tag:
            child = etree.SubElement(self, tag)
        self.insert(index, child)

    def can_remove_child(self, child):
        """
        Checks if a given child can be removed while maintaining validity.

        Args:
            child (FomodElement): The child element to remove.

        Returns:
            bool: Whether the child can be removed.
        """
        if not isinstance(child, FomodElement):
            raise TypeError("child argument must be a FomodElement.")
        elif child not in self:
            raise ValueError("child argument is not a child of this element.")

        index = self.index(child)
        schema_elem, self_copy = self._setup_shallow_schema_and_self()
        self_copy.remove(self_copy[index])
        schema = etree.XMLSchema(schema_elem)
        return schema.validate(self_copy)

    def can_replace_child(self, old_child, new_child):
        """
        Checks if a given child can be replaced while maintaining validity.

        Args:
            old_child (FomodElement): The child element to replaced.
            new_child (FomodElement): The child element to inserted.

        Returns:
            bool: Whether the child can be replaced.
        """
        if not (isinstance(old_child, FomodElement) or
                isinstance(new_child, FomodElement)):
            raise TypeError("child arguments must be a FomodElement.")
        elif (old_child not in self or
              new_child not in self):
            raise ValueError("child argument is not a child of this element.")

        index = self.index(old_child)
        schema_elem, self_copy = self._setup_shallow_schema_and_self()
        self_copy.replace(self_copy[index], etree.Element(new_child.tag))
        schema = etree.XMLSchema(schema_elem)
        return schema.validate(self_copy)

    def can_copy_child(self, child, new_parent):
        """
        Checks if a given child can be copied to a different parent
        while maintaining validity.

        Args:
            child (FomodElement): The child element to copy.
            new_parent (FomodElement): The element where the copy
                will be inserted.

        Returns:
            bool: Whether the child can be copied.
        """
        if not (isinstance(child, FomodElement) or
                isinstance(new_parent, FomodElement)):
            raise TypeError("Arguments must be a FomodElement.")
        elif child not in self:
            raise ValueError("child argument is not a child of this element.")

        return new_parent.can_add_child(child)

    def can_move_child(self, child, new_parent):
        """
        Checks if a given child can be moved to a different parent
        while maintaining validity.

        Args:
            child (FomodElement): The child element to move.
            new_parent (FomodElement): The element where the child
                will be inserted.

        Returns:
            bool: Whether the child can be moved.
        """
        if not (isinstance(child, FomodElement) or
                isinstance(new_parent, FomodElement)):
            raise TypeError("Arguments must be a FomodElement.")
        elif child not in self:
            raise ValueError("child argument is not a child of this element.")

        return new_parent.can_add_child(child) and self.can_remove_child(child)

    def __copy__(self):
        return self.__deepcopy__(None)

    def __deepcopy__(self, memo):
        parent = self.getparent()
        if parent is None:
            copy_elem = self.makeelement(self.tag,
                                         attrib=self.attrib,
                                         nsmap=self.nsmap)
        else:
            copy_elem = etree.SubElement(parent,
                                         self.tag,
                                         attrib=self.attrib,
                                         nsmap=self.nsmap)
            parent.remove(copy_elem)

        copy_elem.text = self.text
        copy_elem.tail = self.tail

        for child in self:
            copy_elem.append(deepcopy(child))

        return copy_elem


class Root(FomodElement):
    """
    This class is used with the 'config' tag.

    It provides access to all values from the 'info.xml' file via properties
    as well as high-level functions and properties to read and modify the
    'ModuleConfig.xml' file.
    """
    pass


class InstallPattern(FomodElement):
    """
    This class is used with the 'pattern' tag under
    'conditionalFileInstalls'.

    It provides access to each pattern's files to be installed
    as well as the corresponding dependency network.
    """
    pass


class Dependencies(FomodElement):
    """
    This class is used with the 'dependencies', 'visible', and
    'moduleDependencies' tags.

    It provides access to a dependencies network. The truth value
    of this class is influenced by its dependency type ('And' or 'Or')
    and by its actual dependencies.
    """
    pass


class InstallStep(FomodElement):
    """
    This class is used with the 'installStep' tag.

    Provides access to a single install step.
    """
    pass


class Group(FomodElement):
    """
    This class is used with the 'group' tag.

    Provides access to a plugin group within an install step.
    """
    pass


class Plugin(FomodElement):
    """
    This class is used with the 'plugin' tag.

    Provides access to a singular plugin and its properties.
    """
    pass


class TypeDependency(FomodElement):
    """
    This class is used with the 'dependencyType' tag.

    Provides access to a list of patterns that determine the
    plugin's type, based on dependencies.
    """
    pass


class TypePattern(FomodElement):
    """
    This class is use with the 'pattern' tag under 'dependencyType'.

    Provides access to a dependency network and the type it sets.
    """
    pass


class _SpecialLookup(etree.CustomElementClassLookup):
    """
    This class is used to lookup and filter outcomments an PI's before we
    get to the tree-based lookup because it REALLY doesn't like to lookup
    comments.
    """
    def lookup(self, node_type, doc, ns, name):
        del doc, ns, name

        if node_type == "comment":
            return etree.CommentBase
        elif node_type == "PI":
            return etree.PIBase
        return None


class _FomodLookup(etree.PythonElementClassLookup):
    """
    The class used to lookup the correct class for key tags in the FOMOD
    document. A full tree based lookup is necessary due to the two pattern
    classes having the same tag name but being essentially different.
    """
    def lookup(self, doc, element):
        del doc  # make pylint shut up

        element_class = FomodElement

        if element.tag == 'config':
            element_class = Root
        elif element.tag in ('dependencies', 'moduleDependencies', 'visible'):
            element_class = Dependencies
        elif element.tag == 'installStep':
            element_class = InstallStep
        elif element.tag == 'group':
            element_class = Group
        elif element.tag == 'plugin':
            element_class = Plugin
        elif element.tag == 'dependencyType':
            element_class = TypeDependency

        # the pattern classes
        # ugh...
        elif element.tag == 'pattern':
            grandparent = element.getparent().getparent()
            if grandparent.tag == "conditionalFileInstalls":
                element_class = InstallPattern
            elif grandparent.tag == "dependencyType":
                element_class = TypePattern

        return element_class


FOMOD_PARSER = etree.XMLParser(remove_blank_text=True)
FOMOD_PARSER.set_element_class_lookup(_SpecialLookup(_FomodLookup()))
