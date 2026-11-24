"""VS display-only node for typed values and engineering units.
Allplan Length/Area/Volume internal input values are mm/mm²/mm³.
"""
from NodeUtil import NodeBase


def create_node(init_data):
    return NodePaletteValueDisplay(init_data)


class NodePaletteValueDisplay(NodeBase):
    SOURCES = {
        'string':'InputString', 'integer':'InputInteger',
        'double':'InputDouble','boolean':'InputBoolean',
        'length':'InputLength','area':'InputArea',
        'volume':'InputVolume','angle':'InputAngle',
    }
    SCALE = {
        'length': {'mm':1.,'cm':10.,'m':1000.},
        'area': {'mm2':1.,'cm2':100.,'m2':1_000_000.},
        'volume': {'mm3':1.,'cm3':1000.,'m3':1_000_000_000.},
        'angle': {'°':1.,'grad':1.},
    }
    DEFAULT_UNIT = {'length':'m','area':'m²','volume':'m³','angle':'°'}
    UNIT_LABEL = {'mm2':'mm²','cm2':'cm²','m2':'m²',
                  'mm3':'mm³','cm3':'cm³','m3':'m³','grad':'°'}

    @staticmethod
    def format_number(value):
        num=float(value)
        if num == 0: num=0
        # German-style decimal comma; 3 decimal places for typical BIM readouts.
        return ('{:,.3f}'.format(num).rstrip('0').rstrip('.')
                .replace(',', 'X').replace('.', ',').replace('X', '.'))

    @classmethod
    def present(cls, kind, value, unit='Auto'):
        if value is None: return '–'
        if kind=='string':return str(value) if value!='' else '–'
        if kind=='boolean':
            return 'Ja' if value is True or str(value).lower() in ('true','1','ja') else 'Nein'
        if kind=='integer':return str(int(value))
        if kind in cls.SCALE:
            specified=(unit or 'Auto').strip()
            if specified.lower()=='auto': specified=cls.DEFAULT_UNIT[kind]
            norm=(specified.replace('²','2').replace('³','3').lower())
            if norm in cls.SCALE[kind]:
                return cls.format_number(float(value)/cls.SCALE[kind][norm]) + ' ' + cls.UNIT_LABEL.get(norm,specified)
            # Unknown explicit unit: reject rather than quietly mislabel numbers.
            raise ValueError('Unsupported unit %s for %s' % (specified,kind))
        if kind=='double':
            text=cls.format_number(value)
            suffix='' if not unit or unit.lower()=='auto' else ' '+unit
            return text+suffix
        return str(value)

    def _create_output(self):
        p=self.build_ele
        kind=str(p.DataType.value or 'Auto').strip().lower()
        # Auto uses first nonempty/nonzero input. Use explicit DataType for a real zero.
        if kind=='auto':
            for name in ('string','length','area','volume','angle','double','integer','boolean'):
                val=getattr(p,self.SOURCES[name]).value
                if val not in (None,'',0,False):
                    kind=name
                    break
            else:
                kind='string'
        if kind not in self.SOURCES:
            raise ValueError('Unknown DataType: %s' % kind)
        value=getattr(p,self.SOURCES[kind]).value
        p.DisplayedText.value=self.present(kind,value,str(p.Unit.value or 'Auto'))
