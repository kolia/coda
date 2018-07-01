using Flux: glorot_uniform

struct Highway{Fh,Sh,Th,Ft,St,Tt}
    gate::Dense{Fh,Sh,Th}
    transform::Dense{Ft,St,Tt}
end

Flux.treelike(Highway)

Highway(dim::Int, σ = relu;
        initWh = glorot_uniform, initbh = zeros,
        initWt = glorot_uniform, initbt = zeros) =
    Highway(
        Dense(dim,dim,Flux.σ; initW=initWh,initb=initbh),
        Dense(dim,dim,σ; initW=initWt,initb=initbt))

function (h::Highway)(x)
    t = h.gate(x)
    t .* h.transform(x) .+ (1 .- t) .* x
end
