module Coda

const Position = Tuple{Symbol,UInt8}

struct Path
    leaf::Any
    path::Vector{Position}
end

struct Arc
    left::Path
    right::Path
end

function paths!(_::Channel{Arc},a::Any) :: Vector{Path}
    [Path(a,[])]
end

function paths!(arcs::Channel{Arc},ex::Expr) :: Vector{Path}
    args = map(collect(pairs(ex.args))) do (i,arg)
        map(paths!(arcs, arg)) do path
            push!(path.path, (ex.head,i))
            path
        end
    end
    for (i,lefts) in enumerate(deepcopy(args)), left in lefts, rights in args[i+1:end], right in rights
        push!(arcs, Arc(left,right))
    end
    isempty(args) ? [] : collect(Iterators.flatten(args))
end

function arcs(ex::Expr) :: Vector{Arc}
    local c = Channel{Arc}(3)
    task = @async paths!(c, ex)
    bind(c, task)
    collect(c)
end


end # module
