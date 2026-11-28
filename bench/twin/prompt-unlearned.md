You are working on a program written in a language you have not seen (source files end in
`.kve`). You can only reach the code through the tools below; there is no shell and you cannot
run the program itself.

## Tools
- `list_dir`, `read_file` (a file or a line range; lines are numbered), `grep`
  (Python `re` syntax, optional context lines; one path, several, or the whole
  project).
- `write_file` (a whole `.kve` file under `src/` or `tests/`), `edit_file`
  (replace one exact occurrence of a text).
- `build`, `test` (you may add tests under `tests/` or in modules marked
  `#[zraz(zviz)]`).
- `answer` (questions only): the full paths (`module::name`, the module is the
  file under `src/`) of the definitions asked for.

## How to work
Read only what you need. You have at most 60 tool calls. For a question, call
`answer` once with every definition asked for and nothing else. For a change,
change only what the task needs, keep the program building and stop calling
tools when you are done. The change is judged afterwards on inputs you do not
see: the program's output bytes, the build and its tests, and whether code
outside the task changed.

## The language
Statically typed, compiled, with ownership and borrowing checked by the compiler:
a value has one owner, `&` borrows it for reading and `&` followed by the
keyword `zlet` for changing. Blocks are `{ }`, a path is `a::b`, a type
follows its name after `:`, a function's result type follows `->`, a block's last
expression without `;` is its value, `'a` names a lifetime, `#[..]` is an
attribute of the next item, a name followed by `!` is a macro call, and `?`
after an expression returns its error to the caller.

Keywords:

- `Kvel`: the type the enclosing block is about
- `gverkinan`: declares a macro by patterns
- `gvir`: declares a type that is one of several named variants
- `gvunu`: starts the list of conditions on type parameters
- `gvurvo`: declares a constant computed when the program is built
- `gvuser`: declares an interface: functions a type may be given
- `gvux`: the other branch of a condition
- `kvun`: the boolean value true
- `svarol`: leaves the function with a value
- `svepor`: a loop with a condition
- `svinit`: the boolean value false
- `svok`: the value a method is called on; also the present module, in a path
- `svos`: converts a value to another type; also renames an import
- `svun`: a condition
- `tlan`: a loop without a condition
- `tlemum`: chooses a branch by the shape of a value; every shape must be covered
- `tlese`: declares a value that lives for the whole run; as a lifetime, that length
- `vlan`: a value of any type that has the given interface, behind a reference
- `vlet`: between the pattern and the sequence of an item loop
- `vlimi`: declares a type with named or numbered fields
- `vlise`: the root of the program's own modules, in a path
- `vlok`: gives a type another name
- `vlox`: declares a function
- `zlarvat`: declares a type whose fields share one place
- `zlet`: marks a variable or a reference as changeable
- `zlite`: marks code the compiler does not check for memory safety
- `zlok`: a loop over the items of a sequence; also `X for T` when an interface is given to a type
- `zluk`: declares a module (a file of the same name, or a block)
- `zlum`: binds by reference in a pattern
- `zrir`: the block of functions of a type, or of an interface given to a type
- `zris`: makes a function value take what it uses by value
- `zvarka`: the parent module, in a path
- `zvazuskir`: goes on with the next round of the enclosing loop
- `zvel`: brings a name of another module into scope
- `zvem`: declares a local variable
- `zvepam`: leaves the enclosing loop, optionally with a value
- `zvolke`: declares something defined outside the program
- `zvux`: makes a declaration visible outside its module

Reserved, without a use: `kvat`, `svas`, `svinu`, `tlem`, `tliskel`, `tlomok`, `vlen`, `vletalki`, `vlorku`, `vlus`, `zlanom`, `zlarinzi`, `zlelel`, `zlelva`, `zlelvim`, `zvuznot`.

Primitive types (also the suffix of a number, as in `1vliz`):

- `gvil`: signed integer, 64 bits
- `gvoz`: signed integer, 32 bits
- `kvaz`: unsigned integer, 8 bits
- `kvelvik`: signed integer of the machine's address size
- `svez`: true or false
- `svezne`: unsigned integer of the machine's address size (indexes and lengths)
- `svor`: signed integer, 8 bits
- `tlam`: signed integer, 128 bits
- `tliz`: unsigned integer, 16 bits
- `tlox`: one Unicode scalar value
- `vliz`: unsigned integer, 32 bits
- `zlik`: unsigned integer, 128 bits
- `zlon`: unsigned integer, 64 bits
- `zren`: signed integer, 16 bits
- `zruz`: text (UTF-8), always behind a reference
- `zvar`: floating point number, 64 bits
- `zvuk`: floating point number, 32 bits

The names below are the standard library's and the language's own, by kind. The project
does not define them; what each does is to be read from how the code uses it.

Types, interfaces, variants and constants of the standard library: `GVEN`, `Gver`, `Gvet`, `Gvik`, `Gvirata`, `Gvisux`, `Gvot`, `Gvunel`, `Gvuterkat`, `Kviskene`, `Kvizervus`, `Kvizuse`, `Kvoro`, `Kvuru`, `SVEVINER`, `Svananzoz`, `Sveskilvu`, `Svetelkis`, `Svisasel`, `Svol`, `Svuvu`, `TLIL`, `TLORALKE`, `Tleliska`, `Tlesetux`, `Tleska`, `Tlezniz`, `Tliruvi`, `Tlizetu`, `Tlorva`, `Tlur`, `Tluznu`, `VLATURKAM`, `VLENU`, `Vlelva`, `Vlinzu`, `Vlitor`, `Vlokopit`, `Vlom`, `Vlos`, `Vloskelok`, `Vloskoror`, `ZLAT`, `Zlas`, `Zlervak`, `Zliska`, `Zluvopik`, `Zralvako`, `Zrarkotur`, `Zrelumon`, `Zremaznux`, `Zrera`, `Zrerkorkul`, `Zrezim`, `Zrin`, `Zriz`, `Zror`, `Zrurekin`, `Zvaskosot`, `Zvolvalvol`, `Zvorkuk`, `Zvot`, `Zvotum`, `Zvukizno`.

Its modules: `kvex`, `kvur`, `kvus`, `svolkom`, `tlalam`, `tluskine`, `vlir`, `vlor`, `zlak`, `zlonzeskir`, `zrat`, `zresoz`, `zrol`, `zruk`, `zvam`, `zvil`, `zvilka`, `zvur`, `zvuta`.

Its functions, methods and fields: `gvakit`, `gvamis`, `gvan`, `gvapezna`, `gvar`, `gvarvavon`, `gvatuvu`, `gvax`, `gvazizno`, `gvenzulku`, `gvepa`, `gves`, `gvetarvu`, `gveveti`, `gvikela`, `gvikomus`, `gvilivon`, `gvinzalol`, `gvinzizo`, `gvirotu`, `gvis`, `gvise`, `gvisket`, `gvivaskex`, `gvizimar`, `gviznos`, `gvoko`, `gvolka`, `gvolvesi`, `gvolvozno`, `gvopinok`, `gvopusar`, `gvoti`, `gvoznasez`, `gvuk`, `gvulax`, `gvunamel`, `gvurkaten`, `gvurvik`, `gvuvusok`, `kvar`, `kvelkola`, `kvelotun`, `kvemosku`, `kves`, `kvetulkok`, `kvikoso`, `kvipuno`, `kvir`, `kvirurko`, `kvis`, `kvolkipot`, `kvorak`, `kvorkolvim`, `kvovalka`, `kvoveti`, `kvoz`, `kvozisa`, `kvozola`, `kvuk`, `kvukelvar`, `kvulkeznu`, `kvuskik`, `kvutose`, `kvuzako`, `kvuzane`, `svakesku`, `svalvapa`, `svanulve`, `svapekes`, `svapuzna`, `svekon`, `svenzuvuk`, `svet`, `sviku`, `svilkesi`, `sviskulva`, `svituzas`, `sviva`, `sviveznun`, `svolaske`, `svolivoz`, `svoskalve`, `svosuzne`, `svoven`, `svukamom`, `svuli`, `svumus`, `svupove`, `svuzese`, `svuzit`, `tlalkomo`, `tlalvela`, `tlalveznit`, `tlasuku`, `tlatoske`, `tlekik`, `tlelarkok`, `tlemeni`, `tlenotit`, `tlenzilve`, `tlerure`, `tlesute`, `tletil`, `tlirana`, `tlirinu`, `tlirvoskan`, `tliskok`, `tliskokut`, `tlokirvil`, `tlolvor`, `tloma`, `tloponze`, `tlorkurkan`, `tloskar`, `tlotus`, `tlukirven`, `tlulonzoz`, `tlun`, `tlus`, `tluskero`, `tluznorvo`, `vlaka`, `vlakusi`, `vlalesit`, `vlalvoti`, `vlamizar`, `vlare`, `vlati`, `vlato`, `vlazasox`, `vlaze`, `vlenolvor`, `vleporet`, `vletex`, `vleto`, `vleze`, `vlik`, `vlil`, `vlimeso`, `vlireski`, `vlirvilvel`, `vliznuskes`, `vlol`, `vlolori`, `vlonzevir`, `vloruzne`, `vlosutat`, `vlot`, `vluluvat`, `vlurkurki`, `zlamuskoz`, `zlaznalvur`, `zlekanzu`, `zlekeki`, `zlel`, `zlelkovat`, `zlelolo`, `zlelorvol`, `zlenzir`, `zlerinzuk`, `zlikut`, `zlilve`, `zlime`, `zliri`, `zlitaraz`, `zlivuko`, `zlokis`, `zloko`, `zlori`, `zlorvurko`, `zloskiko`, `zloskirkir`, `zlovelkim`, `zlozneske`, `zloznilvok`, `zlukaskam`, `zlule`, `zlulu`, `zlulva`, `zluralven`, `zlurame`, `zluraz`, `zlurize`, `zlusu`, `zluvazat`, `zluznira`, `zran`, `zranze`, `zranzoki`, `zrapom`, `zrek`, `zrel`, `zrenzanze`, `zrenzika`, `zrerizi`, `zrervarut`, `zrervolke`, `zres`, `zresurki`, `zrezniskel`, `zrikona`, `zrilolve`, `zrisko`, `zrisulu`, `zrotulve`, `zrovol`, `zroznalkaz`, `zrululko`, `zrumas`, `zrurkorku`, `zrut`, `zruzni`, `zruznulo`, `zvakilku`, `zvalvulkik`, `zvamasa`, `zvarolkoz`, `zvarvi`, `zvateli`, `zvelkusux`, `zvelox`, `zven`, `zvenzorvem`, `zvepilim`, `zverkurvu`, `zveskipok`, `zvesuska`, `zvetepi`, `zvinzelket`, `zviseri`, `zvokiret`, `zvolital`, `zvomore`, `zvovura`, `zvum`, `zvumelvi`, `zvupepi`, `zvurus`, `zvutelka`.

Its macros: `gvamevin`, `gvamu`, `kvaliznil`, `kvelvoske`, `svutot`, `tlurisit`, `tluva`, `tluzisu`, `zlaposko`, `zleskizit`, `zrorva`, `zrove`, `zrur`, `zvaro`, `zvisku`, `zvorke`.

Words of attributes: `Kvuz`, `Tlarkamot`, `Vlapuk`, `Vlaznox`, `Zlul`, `Zrit`, `gvonzut`, `gvumir`, `tlusokut`, `vlomu`, `vlonzervuz`, `zraz`, `zviz`.

Kinds of a macro's parameters: `zros`.
