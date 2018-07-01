
struct CharCNN{N,F,M,A,V}
    in::Int
    out::Int
    embedchar::M
    convs::Vector{Conv{N,F,A,V}}
end

children(c::CharCNN) = [c.embedchar; c.convs]
mapchildren(f, c::CharCNN) = CharCNN(c.in, c.out, f(c.embedchar), map(f, c.convs))

Flux.treelike(CharCNN)

CharCNN(alphabetsize::Int, embedchardim::Int, widthchannels::Vector{Pair{Int,Int}}) =
    CharCNN(
        alphabetsize,
        sum(map(pair -> pair[2], widthchannels)),
        glorot_uniform(embedchardim, alphabetsize),
        map(widthchannels) do wc  # use julia 0.7 destructuring
            Conv(
                (wc[1],1),
                embedchardim=>wc[2],
                tanh)
        end
    )

function (c::CharCNN)(x)
    y = Flux.unsqueeze(Flux.unsqueeze(transpose(c.embedchar * x), 2), 4)
    cat((1), map(conv -> squeeze(maximum(conv(y),(1,)),(1,2,4)), c.convs)...)
end