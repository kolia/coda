import Coda

ast = Meta.parse(read("src/Coda.jl", String))

arcs = Coda.arcs(ast)

dump(arcs)
