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

branches(s::String, rnn) = [Branch([],
    rnn(wordvec(Flux.onehotbatch(Char(1) * transcode(UInt8, s) * Char(1), alphabet))))]

branches(s::Symbol, rnn) = branches(Char(0) * convert(String, s) * Char(0), rnn)

function branches(e::Expr, rnn) :: Vector{Branch}
    if e.head == :module
        return Iterators.flatten(map(e.args) do arg
            branches(arg, rnn)
        end)
    else
        rnn(embed(e.head))
        state = rnn.state
        return Iterators.flatten(map(enumerate(e.args)) do i, arg
            ui = convert(UInt8, min(255, i))
            map(branches(arg, rnn)) do branch
                Branch([ui; branch.path], branch.embedding)
            end
            rnn.state = state
        end)
    end
end
