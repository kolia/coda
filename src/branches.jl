include("src/charcnn.jl")
include("src/highway.jl")

Embedding = Vector{Float64}

charcnn = CharCNN(128, 15, [w=>min(100,25*w) for w in 1:6])
wordvec = Chain(charcnn, Highway(charcnn.out))

down = LSTM(charcnn.out, charcnn.out)
alphabet = collect(0:127)

struct Branch
    path::Vector{UInt8}
    embedding::Embedding
end

function branches(e::Expr)
    Flux.Tracker.reset!(down)
    foreach(p -> p.grad .= 0, Flux.params(down))
    branches(e, down)
end

embed(s::String) =
    wordvec(Flux.onehotbatch(Char(1) * transcode(UInt8, s) * Char(1), alphabet))

embed(s) = embed(Char(0) * convert(String, s) * Char(0))

branches(s, path, rnn) = [Branch(path, embed(s))]

function branches(e::Expr, path, rnn) :: Vector{Branch}
    rnn(embed(e.head))
    state = rnn.state
    return Iterators.flatten(map(enumerate(e.args)) do i, arg
        branches(arg, [convert(UInt8, min(255, i)); path], rnn)
        rnn.state = state
    end)
end
