import { Link } from 'react-router-dom'

const GOOD_TO_KNOW = [
  {
    title: 'Shipping time',
    text: 'Most orders leave our shop within about one to two weeks. Sizes shown as sold out can’t be ordered right now.',
  },
  {
    title: 'Returns within 30 days',
    text: "Send back unworn items with tags still attached within 30 days of shipping. Personalized custom pieces and anything marked final sale can't be returned.",
  },
  {
    title: 'Shipping near and far',
    text: 'We ship across the US and to more than two dozen countries, so Bulldogs abroad can still dress the part.',
  },
]

export default function About() {
  return (
    <>
      <section className="page-hero">
        <div className="page narrow">
          <p className="eyebrow light">About Us</p>
          <h1>Dressing Yale in navy and white since 1975</h1>
          <p className="hero-lead">
            Campus Customs is the New Haven shop behind Yale Bulldog Blue. For half a century, we have helped the Yale
            community wear its colors with pride.
          </p>
        </div>
      </section>

      <section className="page narrow prose">
        <h2>Our story</h2>
        <p>
          Campus Customs has been part of New Haven since 1975, and today our shop sits at 57 Broadway, a short walk
          from campus. We want to be the first stop for a first Yale tee, the easy answer for a move-in gift and the
          place alumni swing by on reunion weekend. Our goal is simple: good Yale gear, made with care.
        </p>

        <h2>What we make</h2>
        <p>
          Campus Customs is a working print shop. Printing and embroidery are our trade, we outfit events too, and
          every Yale design we sell is officially licensed.
        </p>

        <h2>Who we dress</h2>
        <p>
          First-years and grad students, professors and proud parents, and the friends who never miss The Game. We
          carry crest pieces for most of the residential colleges, designs for many of the graduate and professional
          schools, and left-chest logos for Bulldog teams from hockey to sailing. Whatever your corner of Yale, we want you to find yourself on our shelves.
        </p>

        <h2>Our promise</h2>
        <p>
          Shopping should be easy and honest. Our prices and size-by-size availability come straight from our
          inventory, so when we say a size is available, it is. When it isn't, we'll tell you and help you find the
          next best thing.
        </p>
      </section>

      <section className="band">
        <div className="page">
          <header className="section-header">
            <h2>Good to know</h2>
          </header>
          <div className="corner-grid">
            {GOOD_TO_KNOW.map((g) => (
              <article key={g.title} className="corner">
                <h3>{g.title}</h3>
                <p>{g.text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="page">
        <div className="visit-card">
          <div>
            <p className="eyebrow">Find us</p>
            <h2>57 Broadway, New Haven, CT 06511</h2>
            <p>
              Questions about an order? Email{' '}
              <a href="mailto:orderdept@campuscustoms.com">orderdept@campuscustoms.com</a> or call{' '}
              <a href="tel:+14753014205">(475) 301-4205</a>.
            </p>
          </div>
          <Link to="/products" className="btn btn-primary">Browse products</Link>
        </div>
      </section>
    </>
  )
}
